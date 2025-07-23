"""
Solution Agent for Customer Experience Rescue Swarm

This agent analyzes the case file and determines the best resolution path
using company policies retrieved from a RAG knowledge base.
"""

import json
import logging
from typing import Dict, Any, List
from google.cloud import secretmanager
import vertexai
from vertexai.generative_models import GenerativeModel
from tools.policy_lookup_tool import PolicyLookupTool
from tools.order_status_tool import OrderStatusTool
from tools.inventory_check_tool import InventoryCheckTool

logger = logging.getLogger(__name__)

class SolutionAgent:
    """Agent responsible for determining resolution paths using company policies."""
    
    def __init__(self, settings, secret_client: secretmanager.SecretManagerServiceClient):
        self.settings = settings
        self.secret_client = secret_client
        
        # Initialize Vertex AI
        vertexai.init(project=settings.project_id, location=settings.vertex_ai_location)
        self.model = GenerativeModel(settings.language_model)
        
        # Initialize tools
        self.policy_tool = PolicyLookupTool(settings, secret_client)
        self.order_tool = OrderStatusTool(settings, secret_client)
        self.inventory_tool = InventoryCheckTool(settings, secret_client)
    
    def process(self, case_file: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the case file and generate ranked solutions.
        
        Args:
            case_file: Dictionary containing customer details, transcript, and issue summary
            
        Returns:
            Dictionary with ranked solutions
        """
        logger.info("Solution Agent processing case file")
        
        try:
            # Extract key information from case file
            customer_details = case_file.get('customer_details', {})
            transcript_text = case_file.get('transcript_text', '')
            issue_summary = case_file.get('issue_summary', '')
            
            # Step 1: Analyze the issue to understand the problem type
            problem_analysis = self._analyze_problem_type(issue_summary, transcript_text)
            
            # Step 2: Look up relevant policies
            policy_context = self._gather_policy_context(problem_analysis, customer_details)
            
            # Step 3: Get operational data if needed
            operational_data = self._gather_operational_data(problem_analysis, transcript_text)
            
            # Step 4: Generate ranked solutions
            solutions = self._generate_solutions(
                case_file, problem_analysis, policy_context, operational_data
            )
            
            return {
                'ranked_solutions': solutions,
                'problem_analysis': problem_analysis,
                'policy_context': policy_context,
                'operational_data': operational_data
            }
            
        except Exception as e:
            logger.error(f"Error in solution processing: {str(e)}")
            return {'error': str(e), 'ranked_solutions': []}
    
    def _analyze_problem_type(self, issue_summary: str, transcript_text: str) -> Dict[str, Any]:
        """
        Analyze the problem to categorize the issue type.
        
        Args:
            issue_summary: Brief summary of the issue
            transcript_text: Full conversation transcript
            
        Returns:
            Dictionary with problem analysis
        """
        prompt = f"""Analyze this customer issue to determine the problem category and key details.

Issue Summary: {issue_summary}

Transcript: {transcript_text[:2000]}...

Categorize this issue into one or more of these types:
- ORDER_ISSUE: Problems with orders (delays, wrong items, damaged goods)
- BILLING_ISSUE: Payment, refund, or billing problems
- PRODUCT_ISSUE: Product defects or quality issues
- SERVICE_ISSUE: Poor service experience or support issues
- SHIPPING_ISSUE: Delivery problems or shipping concerns
- ACCOUNT_ISSUE: Account access or profile problems

Also extract:
- Order ID (if mentioned)
- Product names/SKUs (if mentioned)
- Specific complaint details
- Customer emotions/urgency level

Respond with JSON:
{{
  "primary_category": "category",
  "secondary_categories": ["other categories"],
  "order_id": "order_id or null",
  "products": ["product names"],
  "complaint_details": ["specific issues"],
  "urgency_level": "low/medium/high/critical"
}}"""

        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            if result_text.startswith('```json'):
                result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            analysis = json.loads(result_text)
            logger.info(f"Problem analysis completed: {analysis.get('primary_category')}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in problem analysis: {str(e)}")
            return {
                'primary_category': 'SERVICE_ISSUE',
                'urgency_level': 'high',
                'error': str(e)
            }
    
    def _gather_policy_context(self, problem_analysis: Dict[str, Any], 
                             customer_details: Dict[str, Any]) -> str:
        """
        Retrieve relevant company policies for the identified problem.
        
        Args:
            problem_analysis: Analysis of the problem type
            customer_details: Customer information
            
        Returns:
            Relevant policy text
        """
        try:
            # Build query based on problem type and customer tier
            problem_category = problem_analysis.get('primary_category', 'SERVICE_ISSUE')
            customer_tier = customer_details.get('status', 'Standard')
            
            # Create targeted policy queries
            queries = [
                f"{problem_category.lower()} policy for {customer_tier} tier customer",
                f"refund policy {customer_tier} customer",
                f"appeasement guidelines {problem_category.lower()}",
                "escalation procedures high value customer"
            ]
            
            all_policies = []
            for query in queries:
                policies = self.policy_tool.search_policies(query)
                if policies:
                    all_policies.append(policies)
            
            return "\n\n".join(all_policies)
            
        except Exception as e:
            logger.error(f"Error gathering policy context: {str(e)}")
            return "Error retrieving policies"
    
    def _gather_operational_data(self, problem_analysis: Dict[str, Any], 
                               transcript_text: str) -> Dict[str, Any]:
        """
        Gather operational data like order status and inventory.
        
        Args:
            problem_analysis: Analysis of the problem type
            transcript_text: Full conversation transcript
            
        Returns:
            Dictionary with operational data
        """
        operational_data = {}
        
        try:
            # Get order status if order ID is mentioned
            order_id = problem_analysis.get('order_id')
            if order_id:
                order_status = self.order_tool.get_order_status(order_id)
                operational_data['order_status'] = order_status
            
            # Check inventory for mentioned products
            products = problem_analysis.get('products', [])
            if products:
                inventory_info = {}
                for product in products:
                    inventory = self.inventory_tool.check_availability(product)
                    inventory_info[product] = inventory
                operational_data['inventory'] = inventory_info
            
            return operational_data
            
        except Exception as e:
            logger.error(f"Error gathering operational data: {str(e)}")
            return {}
    
    def _generate_solutions(self, case_file: Dict[str, Any], 
                          problem_analysis: Dict[str, Any],
                          policy_context: str, operational_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate ranked solutions based on all available context.
        
        Args:
            case_file: Original case file
            problem_analysis: Problem categorization
            policy_context: Relevant policies
            operational_data: Order and inventory data
            
        Returns:
            List of ranked solutions
        """
        prompt = f"""You are a master Solution Agent. Generate ranked solutions for this customer case.

CASE FILE:
{json.dumps(case_file, indent=2)}

PROBLEM ANALYSIS:
{json.dumps(problem_analysis, indent=2)}

RELEVANT POLICIES:
{policy_context}

OPERATIONAL DATA:
{json.dumps(operational_data, indent=2)}

Instructions:
1. Analyze the customer's problem, value, and available policies
2. Generate 2-3 concrete, ranked solutions in order of preference
3. Each solution should specify exact actions and parameters
4. Consider customer tier, problem severity, and company policies
5. Prioritize solutions that restore customer confidence

Available Actions:
- full_refund: Full refund for order
- partial_refund: Partial refund with amount
- reship_order: Resend order with shipping upgrade
- generate_coupon: Create discount coupon
- account_credit: Add credit to customer account
- expedite_shipping: Upgrade shipping on pending order
- escalate_to_manager: Human escalation
- custom_appeasement: Custom resolution

Format your response as JSON:
{{
  "ranked_solutions": [
    {{
      "solution_id": 1,
      "action": "action_name",
      "params": {{"param1": "value1", "param2": "value2"}},
      "explanation": "Why this is the best solution",
      "estimated_cost": "dollar amount or 'low/medium/high'",
      "customer_impact": "expected customer satisfaction outcome"
    }}
  ]
}}"""

        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            if result_text.startswith('```json'):
                result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            solutions_data = json.loads(result_text)
            solutions = solutions_data.get('ranked_solutions', [])
            
            # Validate solutions structure
            for i, solution in enumerate(solutions):
                if not all(key in solution for key in ['solution_id', 'action', 'params', 'explanation']):
                    logger.warning(f"Solution {i+1} missing required fields")
            
            logger.info(f"Generated {len(solutions)} solutions")
            return solutions
            
        except Exception as e:
            logger.error(f"Error generating solutions: {str(e)}")
            return [{
                'solution_id': 1,
                'action': 'escalate_to_manager',
                'params': {'reason': 'Error in automated solution generation'},
                'explanation': 'Due to processing error, escalating to human manager',
                'error': str(e)
            }]