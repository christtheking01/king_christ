import re
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
from .models import TithePayment
from .sms_service import sms_service 

logger = logging.getLogger(__name__)

def format_phone_number(phone):
    """
    Standardizes numbers to +255XXXXXXXXX for Africa's Talking.
    AT requires the '+' prefix for all sandbox and production messages.
    """
    if not phone:
        return None
    # Remove all non-numeric characters
    cleaned = re.sub(r'\D', '', str(phone))
    
    # Handle Tanzanian numbers specifically
    if cleaned.startswith('0'):
        return '+255' + cleaned[1:]
    elif cleaned.startswith('255'):
        return '+' + cleaned
    # Add '+' if international number is missing it
    elif not cleaned.startswith('+') and len(cleaned) in [11, 12, 13]: # Check common lengths
         return '+' + cleaned
    return phone

@receiver(post_save, sender=TithePayment)
def send_tithe_sms_notification(sender, instance, created, **kwargs):
    """
    Signal to send SMS via Africa's Talking when a TithePayment is recorded,
    and update the instance fields with the SMS result.
    """
    # 1. Feature Toggle & Only act on creation
    if not getattr(settings, 'SEND_SMS_ENABLED', False) or not created:
        return

    try:
        # 2. Validate Contact Number
        raw_phone = getattr(instance, 'contact_number', None)
        if not raw_phone:
            logger.warning(f"Tithe ID {instance.id}: No contact number provided.")
            return
        
        phone_number = format_phone_number(raw_phone)
        
        # 3. Data Preparation
        # Fetch member name from related model or default to 'Mpendwa'
        member_name = instance.name.name if hasattr(instance.name, 'name') else "Mpendwa"
        formatted_amount = "{:,}".format(instance.amount)
        
        message = (
            f"Bwana Yesu Asifiwe {member_name}, tunakushukuru kwa zaka yako ya "
            f"Tsh {formatted_amount} imepokelewa. Malaki 3:10. Ubarikiwe sana!"
        )

        # 4. Dispatch SMS
        result = sms_service.send_sms(phone_number, message)
        
        # 5. CRITICAL FIX: Update the model instance fields with the result
        instance.sms_sent_at = timezone.now()
        instance.sms_message_id = result.get('message_id')

        if result.get('success'):
            instance.sms_sent = True
            instance.last_sms_error = None
            logger.info(f"SMS SUCCESS: ID {instance.id} via {result.get('provider')}")
        else:
            instance.sms_sent = False
            instance.sms_failure_count += 1
            instance.last_sms_error = result.get('error')
            logger.error(f"SMS FAILURE: ID {instance.id} | Error: {result.get('error')}")

        # 6. CRITICAL FIX: Save the instance again using update_fields 
        # This prevents the post_save signal from running in an infinite loop
        instance.save(update_fields=[
            'sms_sent', 'sms_sent_at', 'sms_message_id', 
            'sms_failure_count', 'last_sms_error'
        ])
            
    except Exception as e:
        logger.error(f"CRITICAL SIGNAL ERROR for Tithe ID {instance.id}: {str(e)}", exc_info=True)
