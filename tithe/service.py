from django.conf import settings
from .sms_api.africastalking import AfricaTalkingProvider
from .sms_api.BeemAfrica import BeemAfrica
import logging

logger = logging.getLogger(__name__)

class SMSService:
    def __init__(self):
        # Default provider is Africa's Talking
        self.provider = AfricaTalkingProvider(
            username=getattr(settings, 'AFRICASTALKING_USERNAME', 'sandbox'), # Uses 'sandbox' if setting is missing
            api_key=getattr(settings, 'AFRICASTALKING_API_KEY', ''),          # Uses '' if setting is missing
            sender_id=getattr(settings, 'AFRICASTALKING_SENDER_ID', None)
        )
        logger.info(f"SMSService initialized using {self.provider.__class__.__name__}")
    
    def send_sms(self, phone_number, message):
        return self.provider.send_sms(phone_number, message)

# Global instance
sms_service = SMSService()
