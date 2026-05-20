import re
import logging
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
from .models import TithePayment
from .sms_service import sms_service 

logger = logging.getLogger(__name__)

SWAHILI_MONTHS = {
    1: 'Januari',
    2: 'Februari',
    3: 'Machi',
    4: 'Aprili',
    5: 'Mei',
    6: 'Juni',
    7: 'Julai',
    8: 'Agosti',
    9: 'Septemba',
    10: 'Oktoba',
    11: 'Novemba',
    12: 'Desemba'
}

def get_swahili_month(date):
    """Get Swahili month name from a date object"""
    if not date:
        return ''
    month_num = date.month
    return SWAHILI_MONTHS.get(month_num, '')

def format_phone_number(phone):
    if not phone:
        return None
    cleaned = re.sub(r'\D', '', str(phone))
    
    if cleaned.startswith('0'):
        return '+255' + cleaned[1:]
    elif cleaned.startswith('255'):
        return '+' + cleaned
    elif not cleaned.startswith('+') and len(cleaned) in [11, 12, 13]:
         return '+' + cleaned
    return phone

@receiver(post_save, sender=TithePayment)
def send_tithe_sms_notification(sender, instance, created, **kwargs):
    if not getattr(settings, 'SEND_SMS_ENABLED', False):
        return

    if getattr(instance, '_tithe_sms_processed', False):
        return

    # Send SMS for new tithe payments, or on update when no SMS has been sent yet.
    if not created and instance.sms_sent:
        return

    try:
        instance._tithe_sms_processed = True
        raw_phone = getattr(instance, 'contact_number', None)
        if not raw_phone:
            logger.warning(f"Tithe ID {instance.id}: No contact number provided.")
            return
        
        phone_number = format_phone_number(raw_phone)
        
        member_name = instance.name.name if hasattr(instance.name, 'name') else "Mpendwa"
        formatted_amount = "{:,}".format(instance.amount)
        month_name = get_swahili_month(instance.date)
        
        message = (
            f"Parokia ya Kristo Mfalme: Tumsifu Yesu Kristu; mpendwa {member_name} "
            f"zaka ya {month_name} Tsh {formatted_amount} imepokelewa kwa maendeleo ya parokia. Malaki 3:10. Ubarikiwe!"
        )

        result = sms_service.send_sms(phone_number, message)
        
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

        instance.save(update_fields=[
            'sms_sent', 'sms_sent_at', 'sms_message_id', 
            'sms_failure_count', 'last_sms_error'
        ])
            
    except Exception as e:
        logger.error(f"SMS Error for Tithe ID {instance.id}: {str(e)}", exc_info=True)


@receiver(pre_save, sender=TithePayment)
def log_tithe_update(sender, instance, **kwargs):
    """
    Signal triggered before tithe payment is updated.
    Logs the changes and can trigger additional actions.
    """
    if instance.pk:  # Only for existing records (not new ones)
        try:
            old_instance = TithePayment.objects.get(pk=instance.pk)
            
            # Log significant field changes
            changes = []
            if old_instance.amount != instance.amount:
                changes.append(f"Amount: {old_instance.amount} -> {instance.amount}")
            if old_instance.name != instance.name:
                changes.append(f"Member: {old_instance.name} -> {instance.name}")
            if old_instance.status != instance.status:
                changes.append(f"Status: {old_instance.status} -> {instance.status}")
            if old_instance.contact_number != instance.contact_number:
                changes.append(f"Contact: {old_instance.contact_number} -> {instance.contact_number}")
            
            if changes:
                logger.info(f"Tithe ID {instance.id} update: {', '.join(changes)}")
                
                # Optional: Send SMS notification for significant changes
                if getattr(settings, 'SEND_SMS_ENABLED', False):
                    _send_update_notification(instance, old_instance, changes)
                    
        except TithePayment.DoesNotExist:
            logger.warning(f"Tithe ID {instance.pk} not found for update logging")
        except Exception as e:
            logger.error(f"Error logging tithe update for ID {instance.id}: {str(e)}")


@receiver(post_delete, sender=TithePayment)
def log_tithe_deletion(sender, instance, **kwargs):
    """
    Signal triggered after tithe payment is deleted.
    Logs the deletion and can trigger cleanup actions.
    """
    try:
        member_name = instance.name.name if hasattr(instance.name, 'name') else str(instance.name)
        logger.info(f"Tithe payment deleted: ID {instance.id}, Member: {member_name}, Amount: {instance.amount}, Date: {instance.date}")
        
        # Optional: Send notification about deletion
        if getattr(settings, 'SEND_SMS_ENABLED', False) and instance.contact_number:
            _send_deletion_notification(instance)
            
    except Exception as e:
        logger.error(f"Error logging tithe deletion for ID {instance.id}: {str(e)}")


def _send_update_notification(instance, old_instance, changes):
    """
    Helper function to send SMS notification for tithe updates.
    """
    try:
        phone_number = format_phone_number(instance.contact_number)
        if not phone_number:
            return
            
        member_name = instance.name.name if hasattr(instance.name, 'name') else "Mpendwa"
        month_name = get_swahili_month(instance.date)
        
        message = (
            f"Tumsifu Yesu Kristu,{member_name}, zaka yako ya mwezi wa {month_name} "
            f"imebadilishwa kuwa Tsh {instance.amount:,.0f}. Malipo yamesasishwa. Ubarikiwe!"
        )
        
        result = sms_service.send_sms(phone_number, message)
        
        if result.get('success'):
            logger.info(f"Update SMS sent for Tithe ID {instance.id}")
        else:
            logger.error(f"Update SMS failed for Tithe ID {instance.id}: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Error sending update SMS for Tithe ID {instance.id}: {str(e)}")


def _send_deletion_notification(instance):
    """
    Helper function to send SMS notification about tithe deletion.
    """
    try:
        phone_number = format_phone_number(instance.contact_number)
        if not phone_number:
            return
            
        member_name = instance.name.name if hasattr(instance.name, 'name') else "Mpendwa"
        month_name = get_swahili_month(instance.date)
        
        message = (
            f"Tumsifu Yesu {member_name}, zaka yako ya mwezi wa {month_name} "
            f"Tsh {instance.amount:,.0f} imefutwa. Wasiliana na ofisi. Ubarikiwe!"
        )
        
        result = sms_service.send_sms(phone_number, message)
        
        if result.get('success'):
            logger.info(f"Deletion SMS sent for Tithe ID {instance.id}")
        else:
            logger.error(f"Deletion SMS failed for Tithe ID {instance.id}: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Error sending deletion SMS for Tithe ID {instance.id}: {str(e)}")
