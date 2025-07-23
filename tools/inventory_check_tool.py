"""
Inventory Check Tool

Checks product availability and inventory levels.
"""

import logging
import requests
from typing import Dict, Any, Optional
from google.cloud import secretmanager

logger = logging.getLogger(__name__)

class InventoryCheckTool:
    """Tool for checking product inventory and availability."""
    
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
                logger.error(f"Error retrieving inventory API key: {str(e)}")
                raise
        return self._api_key
    
    def check_availability(self, product_identifier: str) -> Optional[Dict[str, Any]]:
        """
        Check product availability and inventory levels.
        
        Args:
            product_identifier: Product SKU, name, or ID
            
        Returns:
            Dictionary with inventory information or None if not found
        """
        try:
            api_key = self._get_api_key()
            
            # Try different endpoints for product lookup
            product_info = self._lookup_product(product_identifier, api_key)
            if not product_info:
                return None
            
            product_id = product_info.get('id')
            inventory_info = self._get_inventory_levels(product_id, api_key)
            
            # Combine product and inventory information
            result = {
                'product_id': product_id,
                'product_name': product_info.get('name'),
                'sku': product_info.get('sku'),
                'in_stock': inventory_info.get('in_stock', False),
                'quantity_available': inventory_info.get('quantity', 0),
                'restock_date': inventory_info.get('restock_date'),
                'alternative_products': inventory_info.get('alternatives', [])
            }
            
            logger.info(f"Successfully checked inventory for {product_identifier}")
            return result
            
        except Exception as e:
            logger.error(f"Error checking inventory for {product_identifier}: {str(e)}")
            return None
    
    def _lookup_product(self, product_identifier: str, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Look up product by identifier.
        
        Args:
            product_identifier: Product SKU, name, or ID
            api_key: API key for authentication
            
        Returns:
            Product information or None if not found
        """
        try:
            # Try lookup by SKU first
            url = f"{self.settings.inventory_api_base_url}/products/search"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            params = {'q': product_identifier}
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            search_results = response.json()
            products = search_results.get('products', [])
            
            if products:
                # Return the first matching product
                return products[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error looking up product {product_identifier}: {str(e)}")
            return None
    
    def _get_inventory_levels(self, product_id: str, api_key: str) -> Dict[str, Any]:
        """
        Get inventory levels for a specific product.
        
        Args:
            product_id: Product ID
            api_key: API key for authentication
            
        Returns:
            Inventory information
        """
        try:
            url = f"{self.settings.inventory_api_base_url}/inventory/{product_id}"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            inventory_data = response.json()
            
            return {
                'in_stock': inventory_data.get('quantity', 0) > 0,
                'quantity': inventory_data.get('quantity', 0),
                'reserved': inventory_data.get('reserved', 0),
                'restock_date': inventory_data.get('expected_restock'),
                'alternatives': inventory_data.get('alternative_products', [])
            }
            
        except Exception as e:
            logger.error(f"Error getting inventory for product {product_id}: {str(e)}")
            return {'in_stock': False, 'quantity': 0}
    
    def reserve_inventory(self, product_id: str, quantity: int = 1) -> bool:
        """
        Reserve inventory for a replacement order.
        
        Args:
            product_id: Product ID
            quantity: Quantity to reserve
            
        Returns:
            True if successful, False otherwise
        """
        try:
            api_key = self._get_api_key()
            
            url = f"{self.settings.inventory_api_base_url}/inventory/{product_id}/reserve"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'quantity': quantity,
                'reason': 'Customer Experience Rescue replacement',
                'reserved_by': 'CX-Rescue-Swarm'
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Successfully reserved {quantity} units of product {product_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error reserving inventory for product {product_id}: {str(e)}")
            return False