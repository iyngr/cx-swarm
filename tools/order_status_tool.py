"""
Order Status Tool

Retrieves order information and status from the order management system.
"""

import logging
import requests
from typing import Dict, Any, Optional
from google.cloud import secretmanager

logger = logging.getLogger(__name__)

class OrderStatusTool:
    """Tool for retrieving order status and details."""
    
    def __init__(self, settings, secret_client: secretmanager.SecretManagerServiceClient):
        self.settings = settings
        self.secret_client = secret_client
        self._api_key = None
    
    def _get_api_key(self) -> str:
        """Retrieve API key from Secret Manager."""
        if self._api_key is None:
            try:
                response = self.secret_client.access_secret_version(
                    request={"name": self.settings.secrets['inventory_api_key']}
                )
                self._api_key = response.payload.data.decode("UTF-8")
            except Exception as e:
                logger.error(f"Error retrieving API key: {str(e)}")
                raise
        return self._api_key
    
    def get_order_status(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve order status and details.
        
        Args:
            order_id: The order identifier
            
        Returns:
            Dictionary with order information or None if not found
        """
        try:
            api_key = self._get_api_key()
            
            url = f"{self.settings.inventory_api_base_url}/orders/{order_id}"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            logger.info(f"Looking up order {order_id}")
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            order_data = response.json()
            
            # Format order information
            formatted_order = {
                'order_id': order_data.get('id', order_id),
                'status': order_data.get('status', 'unknown'),
                'order_date': order_data.get('created_at'),
                'total_amount': order_data.get('total', 0),
                'items': order_data.get('items', []),
                'shipping_address': order_data.get('shipping_address'),
                'tracking_number': order_data.get('tracking_number'),
                'estimated_delivery': order_data.get('estimated_delivery'),
                'shipping_method': order_data.get('shipping_method'),
                'payment_status': order_data.get('payment_status')
            }
            
            logger.info(f"Successfully retrieved order {order_id} with status {formatted_order['status']}")
            return formatted_order
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error looking up order {order_id}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error looking up order {order_id}: {str(e)}")
            return None
    
    def update_order_notes(self, order_id: str, note: str) -> bool:
        """
        Add a note to the order record.
        
        Args:
            order_id: The order identifier
            note: Note to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            api_key = self._get_api_key()
            
            url = f"{self.settings.inventory_api_base_url}/orders/{order_id}/notes"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'note': note,
                'created_by': 'CX-Rescue-Swarm'
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Successfully added note to order {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding note to order {order_id}: {str(e)}")
            return False