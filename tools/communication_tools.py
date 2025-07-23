"""
Communication Tools

Tools for sending emails and SMS messages to customers.
"""

import os
import logging
import requests
from typing import Dict, Any, Optional
from google.cloud import secretmanager

logger = logging.getLogger(__name__)

class EmailTool:
    """Tool for sending emails using SendGrid."""
    
    def __init__(self, settings, secret_client: secretmanager.SecretManagerServiceClient):
        self.settings = settings
        self.secret_client = secret_client
        self._api_key = None
    
    def _get_api_key(self) -> str:
        """Retrieve SendGrid API key from Secret Manager."""
        if self._api_key is None:
            try:
                response = self.secret_client.access_secret_version(
                    request={"name": self.settings.secrets['sendgrid_api_key']}
                )
                self._api_key = response.payload.data.decode("UTF-8")
            except Exception as e:
                logger.error(f"Error retrieving SendGrid API key: {str(e)}")
                raise
        return self._api_key
    
    def send_email(self, recipient: str, subject: str, body: str, 
                   sender: str = None) -> Dict[str, Any]:
        """
        Send an email to a customer.
        
        Args:
            recipient: Recipient email address
            subject: Email subject
            body: Email body content
            sender: Sender email (optional, uses default)
            
        Returns:
            Dictionary with sending results
        """
        try:
            api_key = self._get_api_key()
            
            url = "https://api.sendgrid.com/v3/mail/send"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            from_email = sender or self.settings.sendgrid_from_email
            
            payload = {
                "personalizations": [{
                    "to": [{"email": recipient}],
                    "subject": subject
                }],
                "from": {"email": from_email},
                "content": [{
                    "type": "text/html",
                    "value": self._format_html_email(body)
                }],
                "categories": ["cx-rescue-swarm"],
                "custom_args": {
                    "source": "cx_rescue_swarm",
                    "type": "service_recovery"
                }
            }
            
            logger.info(f"Sending email to {recipient}")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            return {
                'success': True,
                'recipient': recipient,
                'subject': subject,
                'message_id': response.headers.get('X-Message-Id')
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error sending email to {recipient}: {str(e)}")
            return {'success': False, 'error': str(e), 'recipient': recipient}
        except Exception as e:
            logger.error(f"Error sending email to {recipient}: {str(e)}")
            return {'success': False, 'error': str(e), 'recipient': recipient}
    
    def _format_html_email(self, body: str) -> str:
        """
        Format plain text body as HTML email.
        
        Args:
            body: Plain text email body
            
        Returns:
            HTML formatted email
        """
        # Convert line breaks to HTML
        html_body = body.replace('\n', '<br>')
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                {html_body}
                <br><br>
                <div style="border-top: 1px solid #eee; padding-top: 20px; margin-top: 20px;">
                    <p style="font-size: 12px; color: #666;">
                        This message was sent by our Customer Experience Rescue system to ensure 
                        your issue is resolved quickly. If you need further assistance, please 
                        contact our support team.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """


class SMSTool:
    """Tool for sending SMS messages using Twilio."""
    
    def __init__(self, settings, secret_client: secretmanager.SecretManagerServiceClient):
        self.settings = settings
        self.secret_client = secret_client
        self._auth_token = None
        self._account_sid = None
    
    def _get_auth_token(self) -> str:
        """Retrieve Twilio auth token from Secret Manager."""
        if self._auth_token is None:
            try:
                response = self.secret_client.access_secret_version(
                    request={"name": self.settings.secrets['twilio_auth_token']}
                )
                self._auth_token = response.payload.data.decode("UTF-8")
            except Exception as e:
                logger.error(f"Error retrieving Twilio auth token: {str(e)}")
                raise
        return self._auth_token
    
    def send_sms(self, recipient: str, message: str, 
                 from_number: str = None) -> Dict[str, Any]:
        """
        Send an SMS message to a customer.
        
        Args:
            recipient: Recipient phone number (E.164 format)
            message: SMS message content
            from_number: Sender phone number (optional)
            
        Returns:
            Dictionary with sending results
        """
        try:
            auth_token = self._get_auth_token()
            account_sid = os.getenv('TWILIO_ACCOUNT_SID', 'your-account-sid')
            from_phone = from_number or os.getenv('TWILIO_FROM_NUMBER', '+1234567890')
            
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
            
            # Ensure message is within SMS length limits
            if len(message) > 160:
                message = message[:157] + "..."
            
            payload = {
                'To': recipient,
                'From': from_phone,
                'Body': message
            }
            
            # Use HTTP Basic Auth with Account SID and Auth Token
            import base64
            credentials = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
            headers = {
                'Authorization': f'Basic {credentials}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            logger.info(f"Sending SMS to {recipient}")
            response = requests.post(url, headers=headers, data=payload, timeout=30)
            response.raise_for_status()
            
            sms_data = response.json()
            
            return {
                'success': True,
                'recipient': recipient,
                'message_sid': sms_data.get('sid'),
                'status': sms_data.get('status')
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error sending SMS to {recipient}: {str(e)}")
            return {'success': False, 'error': str(e), 'recipient': recipient}
        except Exception as e:
            logger.error(f"Error sending SMS to {recipient}: {str(e)}")
            return {'success': False, 'error': str(e), 'recipient': recipient}