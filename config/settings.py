"""Configuration settings for the Customer Experience Rescue swarm."""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Settings:
    """Configuration settings for the swarm application."""
    
    # Google Cloud Project settings
    project_id: str = os.getenv('GOOGLE_CLOUD_PROJECT', 'your-project-id')
    location: str = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
    
    # Pub/Sub settings
    pubsub_topic: str = 'high_negative_sentiment_alerts'
    subscription_name: str = 'cx-swarm-subscription'
    
    # Vertex AI settings
    vertex_ai_location: str = os.getenv('VERTEX_AI_LOCATION', 'us-central1')
    embedding_model: str = 'text-embedding-004'
    language_model: str = 'gemini-1.5-pro'
    
    # Vector Search settings
    vector_search_index_id: str = os.getenv('VECTOR_SEARCH_INDEX_ID', 'policy-knowledge-base')
    vector_search_endpoint_id: str = os.getenv('VECTOR_SEARCH_ENDPOINT_ID', 'policy-endpoint')
    
    # External API settings
    crm_api_base_url: str = os.getenv('CRM_API_BASE_URL', 'https://api.yourcrm.com')
    inventory_api_base_url: str = os.getenv('INVENTORY_API_BASE_URL', 'https://api.yourinventory.com')
    payment_api_base_url: str = os.getenv('PAYMENT_API_BASE_URL', 'https://api.stripe.com')
    
    # Communication settings
    sendgrid_from_email: str = os.getenv('SENDGRID_FROM_EMAIL', 'support@yourcompany.com')
    
    # Data storage settings
    transcript_dataset: str = os.getenv('BIGQUERY_DATASET', 'customer_data')
    transcript_table: str = os.getenv('BIGQUERY_TABLE', 'call_transcripts')
    
    # Secret Manager secret names
    secrets: dict = None
    
    def __post_init__(self):
        """Initialize secrets configuration."""
        self.secrets = {
            'crm_api_key': f'projects/{self.project_id}/secrets/crm-api-key/versions/latest',
            'inventory_api_key': f'projects/{self.project_id}/secrets/inventory-api-key/versions/latest',
            'payment_api_key': f'projects/{self.project_id}/secrets/payment-api-key/versions/latest',
            'sendgrid_api_key': f'projects/{self.project_id}/secrets/sendgrid-api-key/versions/latest',
            'twilio_auth_token': f'projects/{self.project_id}/secrets/twilio-auth-token/versions/latest',
        }
    
    @property
    def vector_search_index_name(self) -> str:
        """Full Vector Search index name."""
        return f'projects/{self.project_id}/locations/{self.location}/indexes/{self.vector_search_index_id}'
    
    @property
    def vector_search_endpoint_name(self) -> str:
        """Full Vector Search endpoint name."""
        return f'projects/{self.project_id}/locations/{self.location}/indexEndpoints/{self.vector_search_endpoint_id}'