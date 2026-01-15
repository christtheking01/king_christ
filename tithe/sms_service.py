
from django.conf import settings
import africastalking
import logging

logger = logging.getLogger(__name__)

# Initialize Africa's Talking SDK
# Ensure these are in your settings.py (Username should be 'sandbox' for testing)
africastalking.initialize(
    getattr(settings, 'AFRICASTALKING_USERNAME', 'sandbox'),
    getattr(settings, 'AFRICASTALKING_API_KEY', '')
)
at_sms = africastalking.SMS

class SMSService:
    def send_sms(self, phone_number, message):
        """
        Sends SMS via Africa's Talking. 
        Uses Sandbox if username is set to 'sandbox'.
        """
        # 1. Validation for International Format (Required by AT)
        if not phone_number.startswith('+'):
            logger.error(f"Invalid phone format: {phone_number}. Must start with +")
            return {'success': False, 'error': 'Phone number must be in international format (e.g., +255...)'}

        # 2. Get Sender ID (Use None or a Sandbox Shortcode like '12345' for testing)
        sender_id = getattr(settings, 'AFRICASTALKING_SENDER_ID', None)

        try:
            # Prepare parameters
            # AT Python SDK uses 'recipients' (list) and 'message' (string)
            params = {
                'message': message,
                'recipients': [phone_number]
            }
            if sender_id:
                params['sender_id'] = sender_id

            # 3. Send via SDK
            response = at_sms.send(**params)
            
            # 4. Parse Africa's Talking Response
            # Response structure: {'SMSMessageData': {'Message': '...', 'Recipients': [{...}]}}
            recipients = response['SMSMessageData']['Recipients']
            
            if recipients:
                status = recipients[0]['status']
                msg_id = recipients[0].get('messageId', 'no_id')
                
                is_success = status.lower() in ['success', 'sent']

                logger.info(
                    "AT SMS TRANSACTION: To=%s | Status=%s | MsgID=%s",
                    phone_number, status, msg_id
                )

                return {
                    'success': is_success,
                    'message_id': msg_id,
                    'provider': 'africastalking',
                    'data': response
                }

            return {'success': False, 'error': 'No recipient data returned', 'provider': 'africastalking'}

        except Exception as e:
            logger.exception("Africa's Talking SDK Error")
            return {
                'success': False, 
                'error': str(e), 
                'provider': 'africastalking'
            }

# Instantiate for use across the project
sms_service = SMSService()