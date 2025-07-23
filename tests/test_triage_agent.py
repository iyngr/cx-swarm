"""
Tests for the Triage Agent.
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from agents.triage_agent import TriageAgent

class TestTriageAgent:
    """Test cases for the Triage Agent."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_settings = Mock()
        self.mock_settings.project_id = "test-project"
        self.mock_settings.vertex_ai_location = "us-central1"
        self.mock_settings.language_model = "gemini-1.5-pro"
        
        self.mock_secret_client = Mock()
        
        self.test_message = {
            "transcript_id": "T12345",
            "customer_id": "C67890",
            "sentiment_score": 0.95
        }
    
    @patch('agents.triage_agent.vertexai')
    @patch('agents.triage_agent.GenerativeModel')
    @patch('agents.triage_agent.CRMLookupTool')
    @patch('agents.triage_agent.TranscriptRetrievalTool')
    def test_triage_agent_initialization(self, mock_transcript_tool, mock_crm_tool, 
                                       mock_model, mock_vertexai):
        """Test that the triage agent initializes correctly."""
        agent = TriageAgent(self.mock_settings, self.mock_secret_client)
        
        mock_vertexai.init.assert_called_once_with(
            project="test-project", 
            location="us-central1"
        )
        mock_model.assert_called_once_with("gemini-1.5-pro")
        mock_crm_tool.assert_called_once()
        mock_transcript_tool.assert_called_once()
    
    @patch('agents.triage_agent.vertexai')
    @patch('agents.triage_agent.GenerativeModel')
    @patch('agents.triage_agent.CRMLookupTool')
    @patch('agents.triage_agent.TranscriptRetrievalTool')
    def test_process_successful_escalation(self, mock_transcript_tool, mock_crm_tool,
                                         mock_model_class, mock_vertexai):
        """Test successful processing that results in escalation."""
        # Set up mocks
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        
        mock_crm_lookup = Mock()
        mock_crm_lookup.lookup_customer.return_value = {
            'customer_id': 'C67890',
            'ltv': 1500,
            'status': 'Gold',
            'name': 'John Doe'
        }
        mock_crm_tool.return_value = mock_crm_lookup
        
        mock_transcript_lookup = Mock()
        mock_transcript_lookup.get_transcript.return_value = "Customer is very upset about late delivery and says this is the worst experience ever. They want to cancel their account."
        mock_transcript_tool.return_value = mock_transcript_lookup
        
        # Mock LLM response for escalation
        mock_response = Mock()
        mock_response.text = json.dumps({
            "escalate": True,
            "case_file": {
                "customer_details": {
                    'customer_id': 'C67890',
                    'ltv': 1500,
                    'status': 'Gold',
                    'name': 'John Doe'
                },
                "transcript_text": "Customer is very upset...",
                "issue_summary": "Customer extremely upset about late delivery, threatens to cancel account"
            }
        })
        mock_model.generate_content.return_value = mock_response
        
        agent = TriageAgent(self.mock_settings, self.mock_secret_client)
        result = agent.process(self.test_message)
        
        assert result['escalate'] is True
        assert 'case_file' in result
        assert result['case_file']['customer_details']['customer_id'] == 'C67890'
        
        # Verify tools were called
        mock_crm_lookup.lookup_customer.assert_called_once_with('C67890')
        mock_transcript_lookup.get_transcript.assert_called_once_with('T12345')
        mock_model.generate_content.assert_called_once()
    
    @patch('agents.triage_agent.vertexai')
    @patch('agents.triage_agent.GenerativeModel')
    @patch('agents.triage_agent.CRMLookupTool')
    @patch('agents.triage_agent.TranscriptRetrievalTool')
    def test_process_no_escalation_low_value_customer(self, mock_transcript_tool, mock_crm_tool,
                                                    mock_model_class, mock_vertexai):
        """Test processing that doesn't escalate for low-value customer."""
        # Set up mocks
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        
        mock_crm_lookup = Mock()
        mock_crm_lookup.lookup_customer.return_value = {
            'customer_id': 'C67890',
            'ltv': 100,  # Low value customer
            'status': 'Standard',
            'name': 'Jane Doe'
        }
        mock_crm_tool.return_value = mock_crm_lookup
        
        mock_transcript_lookup = Mock()
        mock_transcript_lookup.get_transcript.return_value = "I'm not happy with my order being late."
        mock_transcript_tool.return_value = mock_transcript_lookup
        
        # Mock LLM response for no escalation
        mock_response = Mock()
        mock_response.text = json.dumps({
            "escalate": False,
            "reason": "Customer is low-value and complaint is not severe"
        })
        mock_model.generate_content.return_value = mock_response
        
        agent = TriageAgent(self.mock_settings, self.mock_secret_client)
        result = agent.process(self.test_message)
        
        assert result['escalate'] is False
        assert 'reason' in result
    
    @patch('agents.triage_agent.vertexai')
    @patch('agents.triage_agent.GenerativeModel')
    @patch('agents.triage_agent.CRMLookupTool')
    @patch('agents.triage_agent.TranscriptRetrievalTool')
    def test_process_customer_not_found(self, mock_transcript_tool, mock_crm_tool,
                                      mock_model_class, mock_vertexai):
        """Test handling when customer is not found in CRM."""
        # Set up mocks
        mock_crm_lookup = Mock()
        mock_crm_lookup.lookup_customer.return_value = None  # Customer not found
        mock_crm_tool.return_value = mock_crm_lookup
        
        agent = TriageAgent(self.mock_settings, self.mock_secret_client)
        result = agent.process(self.test_message)
        
        assert result['escalate'] is False
        assert 'Customer not found in CRM' in result['reason']
    
    @patch('agents.triage_agent.vertexai')
    @patch('agents.triage_agent.GenerativeModel')
    @patch('agents.triage_agent.CRMLookupTool')
    @patch('agents.triage_agent.TranscriptRetrievalTool')
    def test_process_transcript_not_found(self, mock_transcript_tool, mock_crm_tool,
                                        mock_model_class, mock_vertexai):
        """Test handling when transcript is not found."""
        # Set up mocks
        mock_crm_lookup = Mock()
        mock_crm_lookup.lookup_customer.return_value = {'customer_id': 'C67890'}
        mock_crm_tool.return_value = mock_crm_lookup
        
        mock_transcript_lookup = Mock()
        mock_transcript_lookup.get_transcript.return_value = None  # Transcript not found
        mock_transcript_tool.return_value = mock_transcript_lookup
        
        agent = TriageAgent(self.mock_settings, self.mock_secret_client)
        result = agent.process(self.test_message)
        
        assert result['escalate'] is False
        assert 'Transcript not found' in result['reason']
    
    @patch('agents.triage_agent.vertexai')
    @patch('agents.triage_agent.GenerativeModel')
    @patch('agents.triage_agent.CRMLookupTool')
    @patch('agents.triage_agent.TranscriptRetrievalTool')
    def test_process_llm_error(self, mock_transcript_tool, mock_crm_tool,
                             mock_model_class, mock_vertexai):
        """Test handling when LLM returns invalid response."""
        # Set up mocks
        mock_model = Mock()
        mock_model_class.return_value = mock_model
        
        mock_crm_lookup = Mock()
        mock_crm_lookup.lookup_customer.return_value = {'customer_id': 'C67890'}
        mock_crm_tool.return_value = mock_crm_lookup
        
        mock_transcript_lookup = Mock()
        mock_transcript_lookup.get_transcript.return_value = "Test transcript"
        mock_transcript_tool.return_value = mock_transcript_lookup
        
        # Mock LLM to return invalid JSON
        mock_response = Mock()
        mock_response.text = "Invalid JSON response"
        mock_model.generate_content.return_value = mock_response
        
        agent = TriageAgent(self.mock_settings, self.mock_secret_client)
        result = agent.process(self.test_message)
        
        assert result['escalate'] is False
        assert 'Analysis error' in result['reason']
    
    @patch('agents.triage_agent.vertexai')
    @patch('agents.triage_agent.GenerativeModel')
    @patch('agents.triage_agent.CRMLookupTool')
    @patch('agents.triage_agent.TranscriptRetrievalTool')
    def test_process_exception_handling(self, mock_transcript_tool, mock_crm_tool,
                                      mock_model_class, mock_vertexai):
        """Test exception handling in process method."""
        # Set up mocks to raise exception
        mock_crm_lookup = Mock()
        mock_crm_lookup.lookup_customer.side_effect = Exception("Database error")
        mock_crm_tool.return_value = mock_crm_lookup
        
        agent = TriageAgent(self.mock_settings, self.mock_secret_client)
        result = agent.process(self.test_message)
        
        assert result['escalate'] is False
        assert 'Processing error' in result['reason']
        assert 'Database error' in result['reason']