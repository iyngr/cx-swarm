"""
Tests for the Customer Experience Rescue Swarm main orchestrator.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from main import CustomerExperienceSwarm

class TestCustomerExperienceSwarm:
    """Test cases for the main swarm orchestrator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.test_message = {
            "transcript_id": "T12345",
            "customer_id": "C67890",
            "sentiment_score": 0.95
        }
    
    @patch('main.secretmanager.SecretManagerServiceClient')
    @patch('main.Settings')
    def test_swarm_initialization(self, mock_settings, mock_secret_client):
        """Test that the swarm initializes correctly."""
        mock_settings.return_value = Mock()
        mock_secret_client.return_value = Mock()
        
        swarm = CustomerExperienceSwarm()
        
        assert swarm.settings is not None
        assert swarm.secret_client is not None
        assert swarm.triage_agent is not None
        assert swarm.solution_agent is not None
        assert swarm.action_agent is not None
    
    @patch('main.secretmanager.SecretManagerServiceClient')
    @patch('main.Settings')
    def test_process_alert_no_escalation(self, mock_settings, mock_secret_client):
        """Test processing when triage agent decides not to escalate."""
        mock_settings.return_value = Mock()
        mock_secret_client.return_value = Mock()
        
        swarm = CustomerExperienceSwarm()
        
        # Mock triage agent to return no escalation
        swarm.triage_agent.process = Mock(return_value={
            'escalate': False,
            'reason': 'Customer does not meet escalation criteria'
        })
        
        result = swarm.process_alert(self.test_message)
        
        assert result['status'] == 'no_action_required'
        assert 'triage_result' in result
        swarm.triage_agent.process.assert_called_once_with(self.test_message)
    
    @patch('main.secretmanager.SecretManagerServiceClient')
    @patch('main.Settings')
    def test_process_alert_successful_resolution(self, mock_settings, mock_secret_client):
        """Test successful end-to-end alert processing."""
        mock_settings.return_value = Mock()
        mock_secret_client.return_value = Mock()
        
        swarm = CustomerExperienceSwarm()
        
        # Mock successful triage
        case_file = {
            'customer_details': {'customer_id': 'C67890', 'ltv': 1500, 'status': 'Gold'},
            'transcript_text': 'Customer is very upset about late delivery...',
            'issue_summary': 'Customer upset about late delivery'
        }
        swarm.triage_agent.process = Mock(return_value={
            'escalate': True,
            'case_file': case_file
        })
        
        # Mock successful solution generation
        solutions = {
            'ranked_solutions': [{
                'solution_id': 1,
                'action': 'full_refund',
                'params': {'order_id': 'O-123', 'amount': 75.50},
                'explanation': 'Full refund for late delivery'
            }]
        }
        swarm.solution_agent.process = Mock(return_value=solutions)
        
        # Mock successful action execution
        action_result = {
            'success': True,
            'refund_processed': True,
            'customer_notified': True
        }
        swarm.action_agent.process = Mock(return_value=action_result)
        
        result = swarm.process_alert(self.test_message)
        
        assert result['status'] == 'success'
        assert result['customer_id'] == 'C67890'
        assert 'case_file' in result
        assert 'solutions' in result
        assert 'actions_taken' in result
        
        # Verify all agents were called
        swarm.triage_agent.process.assert_called_once_with(self.test_message)
        swarm.solution_agent.process.assert_called_once_with(case_file)
        swarm.action_agent.process.assert_called_once_with(case_file, solutions)
    
    @patch('main.secretmanager.SecretManagerServiceClient')
    @patch('main.Settings')
    def test_process_alert_missing_case_file(self, mock_settings, mock_secret_client):
        """Test handling when triage agent escalates but doesn't provide case file."""
        mock_settings.return_value = Mock()
        mock_secret_client.return_value = Mock()
        
        swarm = CustomerExperienceSwarm()
        
        # Mock triage agent to return escalation without case file
        swarm.triage_agent.process = Mock(return_value={
            'escalate': True
            # Missing case_file
        })
        
        result = swarm.process_alert(self.test_message)
        
        assert result['status'] == 'error'
        assert 'Invalid triage result' in result['message']
    
    @patch('main.secretmanager.SecretManagerServiceClient')
    @patch('main.Settings')
    def test_process_alert_solution_agent_error(self, mock_settings, mock_secret_client):
        """Test handling when solution agent fails to generate solutions."""
        mock_settings.return_value = Mock()
        mock_secret_client.return_value = Mock()
        
        swarm = CustomerExperienceSwarm()
        
        # Mock successful triage
        case_file = {
            'customer_details': {'customer_id': 'C67890'},
            'transcript_text': 'Test transcript',
            'issue_summary': 'Test issue'
        }
        swarm.triage_agent.process = Mock(return_value={
            'escalate': True,
            'case_file': case_file
        })
        
        # Mock solution agent failure
        swarm.solution_agent.process = Mock(return_value={
            'ranked_solutions': []  # No solutions generated
        })
        
        result = swarm.process_alert(self.test_message)
        
        assert result['status'] == 'error'
        assert 'No solutions generated' in result['message']
    
    @patch('main.secretmanager.SecretManagerServiceClient')
    @patch('main.Settings')
    def test_process_alert_exception_handling(self, mock_settings, mock_secret_client):
        """Test exception handling in alert processing."""
        mock_settings.return_value = Mock()
        mock_secret_client.return_value = Mock()
        
        swarm = CustomerExperienceSwarm()
        
        # Mock triage agent to raise exception
        swarm.triage_agent.process = Mock(side_effect=Exception("Test error"))
        
        result = swarm.process_alert(self.test_message)
        
        assert result['status'] == 'error'
        assert 'Test error' in result['message']
        assert result['customer_id'] == 'C67890'

@patch('main.base64')
@patch('main.json')
def test_pubsub_handler_valid_message(mock_json, mock_base64):
    """Test Pub/Sub handler with valid message."""
    # Mock cloud event
    cloud_event = Mock()
    cloud_event.data = {'message': {'data': 'encoded_data'}}
    
    # Mock base64 decoding
    mock_base64.b64decode.return_value.decode.return_value = json.dumps({
        "transcript_id": "T12345",
        "customer_id": "C67890",
        "sentiment_score": 0.95
    })
    
    # Mock JSON parsing
    mock_json.loads.return_value = {
        "transcript_id": "T12345", 
        "customer_id": "C67890",
        "sentiment_score": 0.95
    }
    
    with patch('main.CustomerExperienceSwarm') as mock_swarm_class:
        mock_swarm = Mock()
        mock_swarm.process_alert.return_value = {'status': 'success'}
        mock_swarm_class.return_value = mock_swarm
        
        # Import and call the handler
        from main import pubsub_handler
        
        # Should not raise an exception
        pubsub_handler(cloud_event)
        
        mock_swarm.process_alert.assert_called_once()

@patch('main.base64')
@patch('main.json')
def test_pubsub_handler_invalid_message(mock_json, mock_base64):
    """Test Pub/Sub handler with invalid message format."""
    # Mock cloud event
    cloud_event = Mock()
    cloud_event.data = {'message': {'data': 'encoded_data'}}
    
    # Mock base64 decoding
    mock_base64.b64decode.return_value.decode.return_value = json.dumps({
        "transcript_id": "T12345"
        # Missing required fields
    })
    
    # Mock JSON parsing
    mock_json.loads.return_value = {
        "transcript_id": "T12345"
    }
    
    with patch('main.CustomerExperienceSwarm') as mock_swarm_class:
        mock_swarm = Mock()
        mock_swarm_class.return_value = mock_swarm
        
        # Import and call the handler
        from main import pubsub_handler
        
        # Should handle the error gracefully
        pubsub_handler(cloud_event)
        
        # Swarm should not be called with invalid message
        mock_swarm.process_alert.assert_not_called()