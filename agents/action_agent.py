"""
Action & Communication Agent for Customer Experience Rescue Swarm

This agent executes the selected solution and communicates with the customer
to resolve their issue and restore confidence.
"""

import json
import logging
from typing import Dict, Any, List
from google.cloud import secretmanager
import vertexai
from vertexai.generative_models import GenerativeModel
from tools.payment_tools import RefundTool, CouponTool, AccountCreditTool
from tools.shipping_tools import ReshippingTool, ExpediteShippingTool
from tools.communication_tools import EmailTool, SMSTool
from tools.crm_lookup_tool import CRMLookupTool

logger = logging.getLogger(__name__)

class ActionAgent:
    """Agent responsible for executing solutions and communicating with customers."""
    
    def __init__(self, settings, secret_client: secretmanager.SecretManagerServiceClient):
        self.settings = settings
        self.secret_client = secret_client
        
        # Initialize Vertex AI
        vertexai.init(project=settings.project_id, location=settings.vertex_ai_location)
        self.model = GenerativeModel(settings.language_model)
        
        # Initialize execution tools
        self.refund_tool = RefundTool(settings, secret_client)
        self.coupon_tool = CouponTool(settings, secret_client)
        self.credit_tool = AccountCreditTool(settings, secret_client)
        self.reshipping_tool = ReshippingTool(settings, secret_client)
        self.expedite_tool = ExpediteShippingTool(settings, secret_client)
        
        # Initialize communication tools
        self.email_tool = EmailTool(settings, secret_client)
        self.sms_tool = SMSTool(settings, secret_client)
        
        # Initialize CRM tool for logging
        self.crm_tool = CRMLookupTool(settings, secret_client)
    
    def process(self, case_file: Dict[str, Any], solutions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the top solution and communicate with the customer.
        
        Args:
            case_file: Original case file with customer details
            solutions: Ranked solutions from Solution Agent
            
        Returns:
            Dictionary with execution results
        """
        logger.info("Action Agent executing solution")
        
        try:
            ranked_solutions = solutions.get('ranked_solutions', [])
            if not ranked_solutions:
                return {'error': 'No solutions provided', 'success': False}
            
            # Get top solution
            top_solution = ranked_solutions[0]
            customer_details = case_file.get('customer_details', {})
            
            # Step 1: Execute the solution
            execution_result = self._execute_solution(top_solution, customer_details)
            
            # Step 2: Generate and send customer communication
            communication_result = self._send_customer_communication(
                case_file, top_solution, execution_result
            )
            
            # Step 3: Log the incident to CRM
            logging_result = self._log_to_crm(case_file, top_solution, execution_result)
            
            return {
                'success': True,
                'solution_executed': top_solution,
                'execution_result': execution_result,
                'communication_sent': communication_result,
                'crm_logged': logging_result
            }
            
        except Exception as e:
            logger.error(f"Error in action processing: {str(e)}")
            return {'error': str(e), 'success': False}
    
    def _execute_solution(self, solution: Dict[str, Any], 
                         customer_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the specific solution action.
        
        Args:
            solution: Solution dictionary with action and params
            customer_details: Customer information
            
        Returns:
            Dictionary with execution results
        """
        action = solution.get('action')
        params = solution.get('params', {})
        
        logger.info(f"Executing action: {action}")
        
        try:
            if action == 'full_refund':
                return self.refund_tool.process_refund(
                    order_id=params.get('order_id'),
                    amount=params.get('amount'),
                    reason='Customer experience rescue'
                )
            
            elif action == 'partial_refund':
                return self.refund_tool.process_refund(
                    order_id=params.get('order_id'),
                    amount=params.get('amount'),
                    reason='Partial compensation'
                )
            
            elif action == 'reship_order':
                return self.reshipping_tool.create_replacement_order(
                    original_order_id=params.get('order_id'),
                    shipping_upgrade=True
                )
            
            elif action == 'generate_coupon':
                return self.coupon_tool.create_coupon(
                    customer_id=customer_details.get('customer_id'),
                    value=params.get('value'),
                    unit=params.get('unit', 'percent')
                )
            
            elif action == 'account_credit':
                return self.credit_tool.add_credit(
                    customer_id=customer_details.get('customer_id'),
                    amount=params.get('amount'),
                    reason='Service recovery credit'
                )
            
            elif action == 'expedite_shipping':
                return self.expedite_tool.upgrade_shipping(
                    order_id=params.get('order_id'),
                    new_method='express'
                )
            
            elif action == 'escalate_to_manager':
                return {
                    'success': True,
                    'action': 'escalated',
                    'message': 'Case escalated to human manager',
                    'escalation_reason': params.get('reason', 'Complex case requiring human intervention')
                }
            
            else:
                logger.warning(f"Unknown action: {action}")
                return {
                    'success': False,
                    'error': f'Unknown action: {action}'
                }
            
        except Exception as e:
            logger.error(f"Error executing action {action}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'action': action
            }
    
    def _send_customer_communication(self, case_file: Dict[str, Any], 
                                   solution: Dict[str, Any], 
                                   execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate and send empathetic communication to the customer.
        
        Args:
            case_file: Original case file
            solution: Executed solution
            execution_result: Results from execution
            
        Returns:
            Dictionary with communication results
        """
        customer_details = case_file.get('customer_details', {})
        issue_summary = case_file.get('issue_summary', '')
        
        # Generate personalized email content
        email_content = self._generate_email_content(
            customer_details, issue_summary, solution, execution_result
        )
        
        try:
            # Send email if customer has email address
            email_result = None
            if customer_details.get('email'):
                email_result = self.email_tool.send_email(
                    recipient=customer_details['email'],
                    subject=f"We've Resolved Your Recent Concern - {customer_details.get('name', 'Valued Customer')}",
                    body=email_content
                )
            
            # Send SMS if phone number available and execution was successful
            sms_result = None
            if customer_details.get('phone') and execution_result.get('success'):
                sms_content = self._generate_sms_content(solution, execution_result)
                sms_result = self.sms_tool.send_sms(
                    recipient=customer_details['phone'],
                    message=sms_content
                )
            
            return {
                'email_sent': email_result,
                'sms_sent': sms_result,
                'content_generated': True
            }
            
        except Exception as e:
            logger.error(f"Error sending customer communication: {str(e)}")
            return {
                'error': str(e),
                'content_generated': True,
                'email_sent': None,
                'sms_sent': None
            }
    
    def _generate_email_content(self, customer_details: Dict[str, Any], 
                              issue_summary: str, solution: Dict[str, Any],
                              execution_result: Dict[str, Any]) -> str:
        """
        Generate personalized, empathetic email content.
        
        Args:
            customer_details: Customer information
            issue_summary: Summary of the issue
            solution: Solution that was executed
            execution_result: Results from execution
            
        Returns:
            Email content string
        """
        prompt = f"""Generate a personalized, empathetic email to a customer whose issue has been resolved.

Customer Details:
- Name: {customer_details.get('name', 'Valued Customer')}
- Customer Tier: {customer_details.get('status', 'Standard')}
- Issue: {issue_summary}

Solution Executed:
- Action: {solution.get('action')}
- Details: {solution.get('explanation')}

Execution Result:
{json.dumps(execution_result, indent=2)}

Email Requirements:
1. Acknowledge their frustration and apologize sincerely
2. Explain the specific action taken to resolve their issue
3. Mention any compensation or benefits provided
4. Reassure them of our commitment to their satisfaction
5. Provide contact information for follow-up
6. Use a warm, professional tone

Keep the email concise but thorough. Include specific details about what was done."""

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generating email content: {str(e)}")
            # Fallback email template
            return f"""Dear {customer_details.get('name', 'Valued Customer')},

We sincerely apologize for the recent issue you experienced. We have taken immediate action to resolve your concern and ensure your satisfaction.

We understand how frustrating this situation must have been, and we want to make it right.

If you have any questions or concerns, please don't hesitate to reach out to us.

Thank you for your patience and for being a valued customer.

Best regards,
Customer Experience Team"""
    
    def _generate_sms_content(self, solution: Dict[str, Any], 
                            execution_result: Dict[str, Any]) -> str:
        """
        Generate brief SMS notification.
        
        Args:
            solution: Solution that was executed
            execution_result: Results from execution
            
        Returns:
            SMS content string
        """
        action = solution.get('action', '')
        
        if action == 'full_refund':
            return "Good news! Your refund has been processed and should appear in your account within 3-5 business days. Thank you for your patience."
        elif action == 'generate_coupon':
            return "We've added a special discount to your account as an apology for the recent issue. Check your email for details!"
        elif action == 'reship_order':
            return "Your replacement order has been shipped with expedited delivery. You'll receive tracking information shortly."
        else:
            return "We've resolved your recent concern. Please check your email for full details. Thank you for your patience!"
    
    def _log_to_crm(self, case_file: Dict[str, Any], solution: Dict[str, Any], 
                   execution_result: Dict[str, Any]) -> bool:
        """
        Log the incident and resolution to the CRM system.
        
        Args:
            case_file: Original case file
            solution: Solution that was executed
            execution_result: Results from execution
            
        Returns:
            True if successful, False otherwise
        """
        try:
            customer_id = case_file.get('customer_details', {}).get('customer_id')
            if not customer_id:
                return False
            
            # Create comprehensive log entry
            log_entry = f"""CX RESCUE INCIDENT - {case_file.get('issue_summary', 'Customer Issue')}

RESOLUTION DETAILS:
- Action Taken: {solution.get('action')}
- Execution Status: {'SUCCESS' if execution_result.get('success') else 'FAILED'}
- Solution Explanation: {solution.get('explanation')}

CUSTOMER COMMUNICATION:
- Email sent to customer
- Issue resolved automatically by CX Rescue Swarm

FOLLOW-UP:
- Monitor customer satisfaction
- Ensure resolution effectiveness"""
            
            success = self.crm_tool.update_customer_notes(customer_id, log_entry)
            
            if success:
                logger.info(f"Successfully logged incident to CRM for customer {customer_id}")
            else:
                logger.error(f"Failed to log incident to CRM for customer {customer_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error logging to CRM: {str(e)}")
            return False