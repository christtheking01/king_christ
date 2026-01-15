import BeemAfrica  
from ..base import BaseSMSProvider

class BeemAfricaProvider(BaseSMSProvider):
    def __init__(self, api_key, secret_key, sender_id=None):
        # Use the official client initialization
        self.client = BeemAfrica.SMS(api_key=api_key, secret_key=secret_key)
        self.sender_id = sender_id
        super().__init__()
    
    def send_sms(self, phone_number, message):
        try:
            # Correct method call and parameter names
            response = self.client.send_sms(
                message=message,
                recipients=phone_number,  # Accepts string or list
                sender_id=self.sender_id
            )
            
            # Beem Africa response usually contains a 'successful' boolean
            if response.get('successful'):
                return {
                    'success': True,
                    'message_id': response.get('request_id'),
                    'data': response,
                    'provider': 'beemafrica'
                }
            else:
                return {
                    'success': False, 
                    'error': response.get('message', 'Unknown Error'),
                    'data': response
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
