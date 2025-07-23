"""
Payment Tools

Tools for processing refunds, generating coupons, and managing account credits.
"""

import logging
import requests
from typing import Dict, Any, Optional
from google.cloud import secretmanager

logger = logging.getLogger(__name__)

class RefundTool:
    """Tool for processing customer refunds."""
    
    def __init__(self, settings, secret_client: secretmanager.SecretManagerServiceClient):
        self.settings = settings
        self.secret_client = secret_client
        self._api_key = None
    
    def _get_api_key(self) -> str:
        """Retrieve payment API key from Secret Manager."""
        if self._api_key is None:
            try:
                response = self.secret_client.access_secret_version(
                    request={"name": self.settings.secrets['payment_api_key']}
                )
                self._api_key = response.payload.data.decode("UTF-8")
            except Exception as e:
                logger.error(f"Error retrieving payment API key: {str(e)}")
                raise
        return self._api_key
    
    def process_refund(self, order_id: str, amount: float = None, reason: str = None) -> Dict[str, Any]:
        """
        Process a refund for an order.
        
        Args:
            order_id: Order identifier
            amount: Refund amount (None for full refund)
            reason: Reason for refund
            
        Returns:
            Dictionary with refund results
        """
        try:
            api_key = self._get_api_key()
            
            url = f"{self.settings.payment_api_base_url}/v1/refunds"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'charge': order_id,  # Assuming order_id maps to charge ID
                'reason': reason or 'requested_by_customer',
                'metadata': {
                    'source': 'cx_rescue_swarm',
                    'automated': 'true'
                }
            }
            
            if amount:
                payload['amount'] = int(amount * 100)  # Convert to cents for Stripe
            
            logger.info(f"Processing refund for order {order_id}")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            refund_data = response.json()
            
            return {
                'success': True,
                'refund_id': refund_data.get('id'),
                'amount': refund_data.get('amount', 0) / 100,  # Convert back from cents
                'status': refund_data.get('status'),
                'order_id': order_id
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error processing refund for order {order_id}: {str(e)}")
            return {'success': False, 'error': str(e), 'order_id': order_id}
        except Exception as e:
            logger.error(f"Error processing refund for order {order_id}: {str(e)}")
            return {'success': False, 'error': str(e), 'order_id': order_id}


class CouponTool:
    """Tool for generating discount coupons."""
    
    def __init__(self, settings, secret_client: secretmanager.SecretManagerServiceClient):
        self.settings = settings
        self.secret_client = secret_client
        self._api_key = None
    
    def _get_api_key(self) -> str:
        """Retrieve payment API key from Secret Manager."""
        if self._api_key is None:
            try:
                response = self.secret_client.access_secret_version(
                    request={"name": self.settings.secrets['payment_api_key']}
                )
                self._api_key = response.payload.data.decode("UTF-8")
            except Exception as e:
                logger.error(f"Error retrieving payment API key: {str(e)}")
                raise
        return self._api_key
    
    def create_coupon(self, customer_id: str, value: float, unit: str = 'percent') -> Dict[str, Any]:
        """
        Create a discount coupon for a customer.
        
        Args:
            customer_id: Customer identifier
            value: Discount value
            unit: 'percent' or 'amount'
            
        Returns:
            Dictionary with coupon details
        """
        try:
            api_key = self._get_api_key()
            
            # Generate unique coupon code
            import uuid
            coupon_code = f"CX-RESCUE-{uuid.uuid4().hex[:8].upper()}"
            
            url = f"{self.settings.payment_api_base_url}/v1/coupons"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'id': coupon_code,
                'name': f'Customer Experience Rescue - {customer_id}',
                'metadata': {
                    'customer_id': customer_id,
                    'source': 'cx_rescue_swarm',
                    'created_for': 'service_recovery'
                }
            }
            
            if unit == 'percent':
                payload['percent_off'] = value
            else:
                payload['amount_off'] = int(value * 100)  # Convert to cents
                payload['currency'] = 'usd'
            
            logger.info(f"Creating coupon {coupon_code} for customer {customer_id}")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            coupon_data = response.json()
            
            return {
                'success': True,
                'coupon_code': coupon_code,
                'value': value,
                'unit': unit,
                'customer_id': customer_id,
                'coupon_id': coupon_data.get('id')
            }
            
        except Exception as e:
            logger.error(f"Error creating coupon for customer {customer_id}: {str(e)}")
            return {'success': False, 'error': str(e), 'customer_id': customer_id}


class AccountCreditTool:
    """Tool for adding credits to customer accounts."""
    
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
    
    def add_credit(self, customer_id: str, amount: float, reason: str = None) -> Dict[str, Any]:
        """
        Add account credit for a customer.
        
        Args:
            customer_id: Customer identifier
            amount: Credit amount
            reason: Reason for credit
            
        Returns:
            Dictionary with credit results
        """
        try:
            api_key = self._get_api_key()
            
            url = f"{self.settings.crm_api_base_url}/customers/{customer_id}/credits"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'amount': amount,
                'reason': reason or 'Service recovery credit',
                'source': 'cx_rescue_swarm',
                'type': 'service_recovery'
            }
            
            logger.info(f"Adding ${amount} credit to customer {customer_id}")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            credit_data = response.json()
            
            return {
                'success': True,
                'credit_id': credit_data.get('id'),
                'amount': amount,
                'customer_id': customer_id,
                'balance': credit_data.get('new_balance')
            }
            
        except Exception as e:
            logger.error(f"Error adding credit for customer {customer_id}: {str(e)}")
            return {'success': False, 'error': str(e), 'customer_id': customer_id}