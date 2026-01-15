import requests
import base64
from typing import Dict, Any
from ..base import BaseSMSProvider

class NextSMSProvider(BaseSMSProvider):
    def __init__(self, api_key: str, api_secret: str, sender_id: str, base_url: str = "https://apigw.nextsms.com"):
        self.api_key = api_key
        self.api_secret = api_secret  
        self.sender_id = sender_id
        self.base_url = base_url
    
    def _get_auth_header(self):
        # Option 1: Basic Auth (Most common for NextSMS)
        credentials = f"{self.api_key}:{self.api_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        return {
            'Authorization': f'Basic {encoded_credentials}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # OR Option 2: API Key in header (if NextSMS uses this)
        # return {
        #     'apiKey': self.api_key,
        #     'Content-Type': 'application/json',
        #     'Accept': 'application/json'
        # }
    
    def send_sms(self, phone_number: str, message: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/sms/v1/text/single"
        
        payload = {
            "from": self.sender_id,
            "to": self._clean_phone_number(phone_number),
            "text": message
        }
        
        try:
            response = requests.post(
                url, 
                json=payload, 
                headers=self._get_auth_header(), 
                timeout=30,
                verify=True  # Important for production
            )
            response_data = response.json()
            
            # Check for success based on NextSMS response structure
            # NextSMS might return status codes like 200, 201, or use "status" field
            success = response.status_code in [200, 201]
            
            return {
                'success': success,
                'message_id': response_data.get('messageId') or response_data.get('id'),
                'data': response_data,
                'status_code': response.status_code,
                'provider': 'nextsms'
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f"Network error: {str(e)}",
                'provider': 'nextsms'
            }
        except ValueError as e:  # JSON decode error
            return {
                'success': False,
                'error': f"Invalid response: {str(e)}",
                'provider': 'nextsms'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Unexpected error: {str(e)}",
                'provider': 'nextsms'
            }
    
    def send_bulk_sms(self, recipients: list) -> Dict[str, Any]:
        # Implementation for bulk SMS
        # NextSMS bulk endpoint is usually: /api/sms/v1/text/multi
        pass
    
    def get_balance(self) -> Dict[str, Any]:
        # Implementation for balance check
        # NextSMS balance endpoint might be: /api/v1/balance
        url = f"{self.base_url}/api/v1/balance"
        
        try:
            response = requests.get(
                url,
                headers=self._get_auth_header(),
                timeout=30
            )
            response_data = response.json()
            
            return {
                'success': response.status_code == 200,
                'balance': response_data.get('balance'),
                'data': response_data,
                'status_code': response.status_code
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _clean_phone_number(self, phone_number: str) -> str:
        cleaned = ''.join(filter(str.isdigit, str(phone_number)))
        
        # Tanzanian phone number formatting
        if cleaned.startswith('0'):
            cleaned = '255' + cleaned[1:]  # Tanzania country code
        elif cleaned.startswith('+255'):
            cleaned = cleaned[1:]  # Remove the '+'
        elif cleaned.startswith('255'):
            pass  # Already in correct format
        else:
            # If number doesn't match expected patterns, assume it's already correct
            pass
            
        return cleaned