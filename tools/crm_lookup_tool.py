"""
CRM Lookup Tool

Fetches customer data from the CRM system using secure API credentials.
"""

import logging
import requests
from typing import Dict, Any, Optional
from google.cloud import secretmanager

logger = logging.getLogger(__name__)

class CRMLookupTool:
    """Tool for looking up customer information from CRM system."""
    
    def __init__(self, settings, secret_client: secretmanager.SecretManagerServiceClient):
        self.settings = settings
        self.secret_client = secret_client
        self._api_key = None
    
    def _get_api_key(self) -> str:
        """Retrieve CRM API key from Secret Manager."""
        if self._api_key is None:
            try:
                response = self.secret_client.access_secret_version(
                    request={"name": self.settings.secrets['crm_api_key']}
                )
                self._api_key = response.payload.data.decode("UTF-8")
            except Exception as e:
                logger.error(f"Error retrieving CRM API key: {str(e)}")
                raise
        return self._api_key
    
    def lookup_customer(self, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch customer data from CRM.
        
        Args:
            customer_id: The customer's unique identifier
            
        Returns:
            Dictionary with customer details or None if not found
        """
        try:
            api_key = self._get_api_key()
            
            # Construct API request
            url = f"{self.settings.crm_api_base_url}/customers/{customer_id}"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            logger.info(f"Looking up customer {customer_id} in CRM")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            customer_data = response.json()
            
            # Extract and format key customer information
            formatted_data = {
                'customer_id': customer_data.get('id', customer_id),
                'ltv': customer_data.get('lifetime_value', 0),
                'status': customer_data.get('tier', 'Standard'),
                'recent_order_count': customer_data.get('orders_last_90_days', 0),
                'join_date': customer_data.get('created_at'),
                'email': customer_data.get('email'),
                'name': customer_data.get('name', 'Unknown'),
                'phone': customer_data.get('phone'),
                'total_orders': customer_data.get('total_orders', 0),
                'avg_order_value': customer_data.get('avg_order_value', 0),
                'last_order_date': customer_data.get('last_order_date'),
                'support_tickets': customer_data.get('support_tickets_count', 0),
                'satisfaction_score': customer_data.get('satisfaction_score')
            }
            
            logger.info(f"Successfully retrieved customer data for {customer_id}")
            return formatted_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error looking up customer {customer_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error looking up customer {customer_id}: {str(e)}")
            return None
    
    def update_customer_notes(self, customer_id: str, note: str) -> bool:
        """
        Add a note to the customer's record in the CRM.
        
        Args:
            customer_id: The customer's unique identifier
            note: The note to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            api_key = self._get_api_key()
            
            url = f"{self.settings.crm_api_base_url}/customers/{customer_id}/notes"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'note': note,
                'created_by': 'CX-Rescue-Swarm',
                'timestamp': None  # Will be set by CRM system
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Successfully added note to customer {customer_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error adding note for customer {customer_id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error adding note for customer {customer_id}: {str(e)}")
            return False