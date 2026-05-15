from django.conf import settings
import africastalking
import logging

logger = logging.getLogger(__name__)

_at_sms = None

def _get_sms_client():
    """Lazy initialization of Africa's Talking SMS client"""
    global _at_sms
    if _at_sms is None:
        if not getattr(settings, 'SEND_SMS_ENABLED', False):
            logger.warning("SMS sending is disabled. Set SEND_SMS_ENABLED=True to enable.")
            return None
        
        username = getattr(settings, 'AFRICASTALKING_USERNAME', '')
        api_key = getattr(settings, 'AFRICASTALKING_API_KEY', '')
        
        if not username or not api_key:
            logger.error("Africa's Talking credentials not configured. Set AFRICASTALKING_USERNAME and AFRICASTALKING_API_KEY.")
            return None
        
        try:
            africastalking.initialize(username, api_key)
            _at_sms = africastalking.SMS
            logger.info("Africa's Talking SMS client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Africa's Talking: {e}")
            return None
    
    return _at_sms

class SMSService:
    def send_sms(self, phone_number, message):
        if not getattr(settings, 'SEND_SMS_ENABLED', False):
            logger.warning("SMS sending is disabled. Set SEND_SMS_ENABLED=True to enable.")
            return {'success': False, 'error': 'SMS sending is disabled', 'provider': 'africastalking'}
        
        if not phone_number.startswith('+'):
            logger.error(f"Invalid phone format: {phone_number}. Must start with +")
            return {'success': False, 'error': 'Phone number must be in international format (e.g., +255...)'}

        at_sms = _get_sms_client()
        if at_sms is None:
            return {'success': False, 'error': 'SMS client not initialized. Check credentials and SEND_SMS_ENABLED setting.', 'provider': 'africastalking'}

        sender_id = getattr(settings, 'AFRICASTALKING_SENDER_ID', None)

        try:
            # Add prefix to message
            prefixed_message = f"Parokia ya Kristo Mfalme:\n{message}"
            
            params = {
                'message': prefixed_message,
                'recipients': [phone_number]
            }
            if sender_id:
                params['sender_id'] = sender_id

            response = at_sms.send(**params)
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

sms_service = SMSService()