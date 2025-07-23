"""
Customer Experience Rescue Swarm

A multi-agent system deployed on Google Cloud's Agent Engine that automatically
resolves critical customer complaints based on negative sentiment analysis.

The system consists of three main agents:
1. Triage Agent: Validates alerts and gathers context
2. Solution Agent: Determines resolution path using company policies
3. Action & Communication Agent: Executes solutions and communicates with customers
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from google.cloud import pubsub_v1
from google.cloud import secretmanager
from agents.triage_agent import TriageAgent
from agents.solution_agent import SolutionAgent
from agents.action_agent import ActionAgent
from config.settings import Settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CustomerExperienceSwarm:
    """Main orchestrator for the Customer Experience Rescue swarm."""
    
    def __init__(self):
        self.settings = Settings()
        self.secret_client = secretmanager.SecretManagerServiceClient()
        self.triage_agent = TriageAgent(self.settings, self.secret_client)
        self.solution_agent = SolutionAgent(self.settings, self.secret_client)
        self.action_agent = ActionAgent(self.settings, self.secret_client)
        
    def process_alert(self, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a negative sentiment alert through the agent swarm.
        
        Args:
            message_data: Dictionary containing transcript_id, customer_id, sentiment_score
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Processing alert for customer {message_data.get('customer_id')}")
        
        try:
            # Step 1: Triage Agent - Validate and gather context
            logger.info("Step 1: Running Triage Agent")
            triage_result = self.triage_agent.process(message_data)
            
            if not triage_result.get('escalate', False):
                logger.info("Triage agent determined no escalation needed")
                return {
                    'status': 'no_action_required',
                    'message': 'Alert did not meet escalation criteria',
                    'triage_result': triage_result
                }
            
            case_file = triage_result.get('case_file')
            if not case_file:
                logger.error("Triage agent escalated but no case file provided")
                return {'status': 'error', 'message': 'Invalid triage result'}
            
            # Step 2: Solution Agent - Determine resolution path
            logger.info("Step 2: Running Solution Agent")
            solution_result = self.solution_agent.process(case_file)
            
            if not solution_result.get('ranked_solutions'):
                logger.error("Solution agent did not provide valid solutions")
                return {'status': 'error', 'message': 'No solutions generated'}
            
            # Step 3: Action & Communication Agent - Execute and communicate
            logger.info("Step 3: Running Action & Communication Agent")
            action_result = self.action_agent.process(case_file, solution_result)
            
            logger.info("Customer Experience Rescue completed successfully")
            return {
                'status': 'success',
                'customer_id': message_data.get('customer_id'),
                'case_file': case_file,
                'solutions': solution_result,
                'actions_taken': action_result
            }
            
        except Exception as e:
            logger.error(f"Error processing alert: {str(e)}")
            return {
                'status': 'error',
                'message': str(e),
                'customer_id': message_data.get('customer_id')
            }

def pubsub_handler(cloud_event):
    """Cloud Function handler for Pub/Sub trigger."""
    try:
        # Decode the Pub/Sub message
        import base64
        message_data = json.loads(base64.b64decode(cloud_event.data['message']['data']).decode('utf-8'))
        
        # Validate required fields
        required_fields = ['transcript_id', 'customer_id', 'sentiment_score']
        if not all(field in message_data for field in required_fields):
            logger.error(f"Missing required fields in message: {message_data}")
            return
        
        # Process the alert
        swarm = CustomerExperienceSwarm()
        result = swarm.process_alert(message_data)
        
        logger.info(f"Processing result: {result}")
        
    except Exception as e:
        logger.error(f"Error in pubsub_handler: {str(e)}")

if __name__ == "__main__":
    # For local testing
    test_message = {
        "transcript_id": "T12345",
        "customer_id": "C67890", 
        "sentiment_score": 0.95
    }
    
    swarm = CustomerExperienceSwarm()
    result = swarm.process_alert(test_message)
    print(json.dumps(result, indent=2))