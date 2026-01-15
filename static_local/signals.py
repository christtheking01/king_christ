from datetime import timezone
import africastalking
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Notification
from member.models import CommunityLeader 

# Initialize Africa's Talking
sms = africastalking.SMS

@receiver(post_save, sender=Notification)
def send_bulk_community_sms(sender, instance, created, **kwargs):
    if not created:
        return

    recipients = []
    
    # Scenario A: Send to all leaders of a selected community
    if instance.community:
        # Get all leaders linked to this specific community
        leaders = CommunityLeader.objects.filter(community=instance.community)
        # Collect their phone numbers (assuming the field is 'phone_number')
        recipients = [leader.phone_number for leader in leaders if leader.phone_number]
        
    # Scenario B: Send to the single recipient (if no community is selected)
    elif instance.recipient and hasattr(instance.recipient, 'phone_number'):
        recipients = [instance.recipient.phone_number]

    # Send the SMS if we have recipients
    if recipients:
        try:
            # Africa's Talking handles multiple numbers in a single list
            message_body = f"{instance.title}: {instance.message[:150]}"
            response = sms.send(message_body, recipients, sender_id=settings.AFRICASTALKING_SENDER_ID)
            
            # Log the successful send in your notification model
            Notification.objects.filter(pk=instance.pk).update(
                status='sent',
                sent_at=timezone.now()
            )
            print(f"Africa's Talking Response: {response}")
            
        except Exception as e:
            print(f"Bulk SMS Failed: {e}")
