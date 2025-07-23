"""
Triage Agent for Customer Experience Rescue Swarm

This agent validates alerts and gathers initial context about the customer
and their issue to determine if escalation is warranted.
"""

import json
import logging
from typing import Dict, Any, Optional
from google.cloud import secretmanager
import vertexai
from vertexai.generative_models import GenerativeModel
from tools.crm_lookup_tool import CRMLookupTool
from tools.transcript_retrieval_tool import TranscriptRetrievalTool

logger = logging.getLogger(__name__)

class TriageAgent:
    """Agent responsible for validating alerts and gathering initial context."""
    
    def __init__(self, settings, secret_client: secretmanager.SecretManagerServiceClient):
        self.settings = settings
        self.secret_client = secret_client
        
        # Initialize Vertex AI
        vertexai.init(project=settings.project_id, location=settings.vertex_ai_location)
        self.model = GenerativeModel(settings.language_model)
        
        # Initialize tools
        self.crm_tool = CRMLookupTool(settings, secret_client)
        self.transcript_tool = TranscriptRetrievalTool(settings, secret_client)
        
    def process(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the incoming alert and determine if escalation is needed.
        
        Args:
            message_data: Dictionary containing transcript_id, customer_id, sentiment_score
            
        Returns:
            Dictionary with escalation decision and case file if applicable
        """
        customer_id = message_data.get('customer_id')
        transcript_id = message_data.get('transcript_id')
        sentiment_score = message_data.get('sentiment_score')
        
        logger.info(f"Triage processing for customer {customer_id}")
        
        try:
            # Step 1: Get customer data from CRM
            customer_details = self.crm_tool.lookup_customer(customer_id)
            if not customer_details:
                logger.error(f"Could not retrieve customer details for {customer_id}")
                return {'escalate': False, 'reason': 'Customer not found in CRM'}
            
            # Step 2: Get full transcript
            transcript_text = self.transcript_tool.get_transcript(transcript_id)
            if not transcript_text:
                logger.error(f"Could not retrieve transcript {transcript_id}")
                return {'escalate': False, 'reason': 'Transcript not found'}
            
            # Step 3: Analyze with LLM to make escalation decision
            escalation_decision = self._analyze_escalation(
                customer_details, transcript_text, sentiment_score
            )
            
            return escalation_decision
            
        except Exception as e:
            logger.error(f"Error in triage processing: {str(e)}")
            return {'escalate': False, 'reason': f'Processing error: {str(e)}'}
    
    def _analyze_escalation(self, customer_details: Dict[str, Any], 
                          transcript_text: str, sentiment_score: float) -> Dict[str, Any]:
        """
        Analyze customer value and transcript severity to make escalation decision.
        
        Args:
            customer_details: Customer information from CRM
            transcript_text: Full conversation transcript
            sentiment_score: Negative sentiment score (0-1)
            
        Returns:
            Dictionary with escalation decision and case file
        """
        prompt = f"""You are a Triage Agent for critical customer complaints.
Your goal is to assess the situation's severity and escalate if necessary.

Customer Details:
{json.dumps(customer_details, indent=2)}

Sentiment Score: {sentiment_score} (0=neutral, 1=extremely negative)

Transcript:
{transcript_text}

Instructions:
1. Analyze the customer's value (LTV > $500 OR status is Gold/VIP/Premium tier)
2. Analyze the transcript for explicit phrases of severe dissatisfaction:
   - "never again", "worst experience", "reporting you"
   - Threats to leave or switch competitors
   - Demands for refunds or escalation to management
   - Language indicating extreme frustration or anger
3. Consider the high sentiment score ({sentiment_score}) as additional evidence

Decision Criteria:
- Escalate if: Customer is high-value AND transcript confirms severe dissatisfaction
- Do not escalate if: Customer is low-value OR transcript shows mild complaints only

If escalating, create a case_file with:
- customer_details: The full customer information
- transcript_text: The full transcript
- issue_summary: One-sentence summary of the core problem

Respond ONLY with valid JSON in this format:
{{"escalate": true/false, "case_file": {{"customer_details": ..., "transcript_text": "...", "issue_summary": "..."}}}}

OR if not escalating:
{{"escalate": false, "reason": "explanation"}}"""

        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Parse JSON response
            if result_text.startswith('```json'):
                result_text = result_text.replace('```json', '').replace('```', '').strip()
            
            result = json.loads(result_text)
            
            # Validate result structure
            if not isinstance(result, dict) or 'escalate' not in result:
                raise ValueError("Invalid response format from LLM")
            
            if result.get('escalate') and 'case_file' not in result:
                raise ValueError("Escalation decision missing case_file")
            
            logger.info(f"Triage decision: {'ESCALATE' if result.get('escalate') else 'NO ESCALATION'}")
            return result
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            return {'escalate': False, 'reason': f'Analysis error: {str(e)}'}
        except Exception as e:
            logger.error(f"Error in escalation analysis: {str(e)}")
            return {'escalate': False, 'reason': f'LLM error: {str(e)}'}