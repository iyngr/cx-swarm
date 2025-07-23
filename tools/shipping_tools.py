"""
Shipping Tools

Tools for reshipping orders and expediting shipping.
"""

import logging
import requests
from typing import Dict, Any, Optional
from google.cloud import secretmanager

logger = logging.getLogger(__name__)

class ReshippingTool:
    """Tool for creating replacement orders."""
    
    def __init__(self, settings, secret_client: secretmanager.SecretManagerServiceClient):
        self.settings = settings
        self.secret_client = secret_client
        self._api_key = None
    
    def _get_api_key(self) -> str:
        """Retrieve inventory API key from Secret Manager."""
        if self._api_key is None:
            try:
                response = self.secret_client.access_secret_version(
                    request={"name": self.settings.secrets['inventory_api_key']}
                )
                self._api_key = response.payload.data.decode("UTF-8")
            except Exception as e:
                logger.error(f"Error retrieving inventory API key: {str(e)}")
                raise
        return self._api_key
    
    def create_replacement_order(self, original_order_id: str, shipping_upgrade: bool = True) -> Dict[str, Any]:
        """
        Create a replacement order for a customer.
        
        Args:
            original_order_id: Original order identifier
            shipping_upgrade: Whether to upgrade shipping
            
        Returns:
            Dictionary with replacement order results
        """
        try:
            api_key = self._get_api_key()
            
            # First, get the original order details
            original_order = self._get_order_details(original_order_id, api_key)
            if not original_order:
                return {'success': False, 'error': 'Original order not found'}
            
            # Create replacement order
            url = f"{self.settings.inventory_api_base_url}/orders"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            shipping_method = 'express' if shipping_upgrade else original_order.get('shipping_method', 'standard')
            
            payload = {
                'customer_id': original_order.get('customer_id'),
                'items': original_order.get('items', []),
                'shipping_address': original_order.get('shipping_address'),
                'shipping_method': shipping_method,
                'order_type': 'replacement',
                'original_order_id': original_order_id,
                'notes': 'Replacement order created by CX Rescue Swarm',
                'priority': 'high'
            }
            
            logger.info(f"Creating replacement order for {original_order_id}")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            new_order_data = response.json()
            
            return {
                'success': True,
                'new_order_id': new_order_data.get('id'),
                'original_order_id': original_order_id,
                'shipping_method': shipping_method,
                'tracking_number': new_order_data.get('tracking_number'),
                'estimated_delivery': new_order_data.get('estimated_delivery')
            }
            
        except Exception as e:
            logger.error(f"Error creating replacement order for {original_order_id}: {str(e)}")
            return {'success': False, 'error': str(e), 'original_order_id': original_order_id}
    
    def _get_order_details(self, order_id: str, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Get details of the original order.
        
        Args:
            order_id: Order identifier
            api_key: API key for authentication
            
        Returns:
            Order details or None if not found
        """
        try:
            url = f"{self.settings.inventory_api_base_url}/orders/{order_id}"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Error getting order details for {order_id}: {str(e)}")
            return None


class ExpediteShippingTool:
    """Tool for upgrading shipping on existing orders."""
    
    def __init__(self, settings, secret_client: secretmanager.SecretManagerServiceClient):
        self.settings = settings
        self.secret_client = secret_client
        self._api_key = None
    
    def _get_api_key(self) -> str:
        """Retrieve inventory API key from Secret Manager."""
        if self._api_key is None:
            try:
                response = self.secret_client.access_secret_version(
                    request={"name": self.settings.secrets['inventory_api_key']}
                )
                self._api_key = response.payload.data.decode("UTF-8")
            except Exception as e:
                logger.error(f"Error retrieving inventory API key: {str(e)}")
                raise
        return self._api_key
    
    def upgrade_shipping(self, order_id: str, new_method: str = 'express') -> Dict[str, Any]:
        """
        Upgrade shipping method for an existing order.
        
        Args:
            order_id: Order identifier
            new_method: New shipping method
            
        Returns:
            Dictionary with upgrade results
        """
        try:
            api_key = self._get_api_key()
            
            url = f"{self.settings.inventory_api_base_url}/orders/{order_id}/shipping"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'shipping_method': new_method,
                'upgrade_reason': 'Customer experience rescue',
                'waive_upgrade_fee': True,
                'priority': 'high'
            }
            
            logger.info(f"Upgrading shipping for order {order_id} to {new_method}")
            response = requests.patch(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            upgrade_data = response.json()
            
            return {
                'success': True,
                'order_id': order_id,
                'new_shipping_method': new_method,
                'new_estimated_delivery': upgrade_data.get('estimated_delivery'),
                'tracking_number': upgrade_data.get('tracking_number')
            }
            
        except Exception as e:
            logger.error(f"Error upgrading shipping for order {order_id}: {str(e)}")
            return {'success': False, 'error': str(e), 'order_id': order_id}