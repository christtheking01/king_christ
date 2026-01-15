import africastalking
from ..base import BaseSMSProvider

class AfricaTalkingProvider(BaseSMSProvider):
    def __init__(self, username, api_key, sender_id=None):
        # In 2026, ensure username is 'sandbox' for testing
        africastalking.initialize(username, api_key)
        self.sms = africastalking.SMS
        self.sender_id = sender_id
    
    def send_sms(self, phone_number, message):
        try:
            # FIX 1: Ensure phone_number is wrapped in a list
            # FIX 2: Use 'sender_id' instead of 'from_'
            params = {
                'message': message,
                'recipients': [phone_number] 
            }
            
            if self.sender_id:
                params['from_'] = self.sender_id
                
            # The SDK method signature is: send(message, recipients, sender_id=None)
            response = self.sms.send(**params)
            
            if response['SMSMessageData']['Recipients']:
                recipient = response['SMSMessageData']['Recipients'][0]
                # Status "Success" is case-sensitive in some SDK versions
                return {
                    'success': recipient['status'].lower() == 'success',
                    'message_id': recipient.get('messageId'),
                    'data': response,
                    'provider': 'africastalking'
                }
            return {'success': False, 'error': 'No recipients'}
        except Exception as e:
            return {'success': False, 'error': str(e), 'provider': 'africastalking'}