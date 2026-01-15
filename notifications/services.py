import africastalking
from django.conf import settings
from django.utils import timezone
from .models import Notification, NotificationLog

class AfricasTalkingService:
    """Service class for handling AfricasTalking SMS"""
    
    def __init__(self):
        self.username = getattr(settings, 'AFRICASTALKING_USERNAME', '')  
        self.api_key = getattr(settings, 'AFRICASTALKING_API_KEY', '') 
        
        if self.username and self.api_key:
            africastalking.initialize(self.username, self.api_key)
            self.sms = africastalking.SMS
        else:
            self.sms = None
    
    def send_sms(self, phone_numbers, message, sender_id=None):
        """
        Send SMS to multiple recipients
        
        Args:
            phone_numbers: List of phone numbers
            message: Message text
            sender_id: Optional sender ID
            
        Returns:
            dict: Response from AfricasTalking
        """
        if not self.sms:
            return {
                'success': False,
                'error': 'AfricasTalking not configured'
            }
        
        try:
            # Ensure phone_numbers is a list
            if isinstance(phone_numbers, str):
                phone_numbers = [phone_numbers]
            
            # Send SMS
            kwargs = {
                'recipients': phone_numbers,
                'message': message
            }
            
            if sender_id:
                kwargs['sender_id'] = sender_id
            
            response = self.sms.send(**kwargs)
            
            return {
                'success': True,
                'response': response
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


class NotificationService:
    """Service class for handling notifications"""
    
    def __init__(self):
        self.at_service = AfricasTalkingService()
    
    def send_notification(self, notification_id):
        """
        Send notification via SMS
        
        Args:
            notification_id: ID of the notification to send
            
        Returns:
            dict: Status of the operation
        """
        try:
            notification = Notification.objects.get(id=notification_id)
            
            # Update status to SENDING
            notification.status = 'SENDING'
            notification.save()
            
            # Get recipients
            recipients = notification.get_recipients()
            notification.total_recipients = recipients.count()
            notification.save()
            
            if not recipients.exists():
                notification.status = 'FAILED'
                notification.error_message = 'No recipients found'
                notification.save()
                return {
                    'success': False,
                    'error': 'No recipients found'
                }
            
            # Send SMS if enabled
            if notification.send_sms:
                sent_count = 0
                failed_count = 0
                
                for member in recipients:
                    if not member.telephone:
                        # Create log for failed send
                        NotificationLog.objects.create(
                            notification=notification,
                            member=member,
                            phone_number='N/A',
                            status='FAILED',
                            error_message='No phone number'
                        )
                        failed_count += 1
                        continue
                    
                    phone_number = str(member.telephone)
                    
                    # Send SMS to individual
                    result = self.at_service.send_sms(
                        phone_numbers=[phone_number],
                        message=notification.message
                    )
                    
                    if result['success']:
                        # Parse response
                        response_data = result.get('response', {})
                        sms_recipients = response_data.get('SMSMessageData', {}).get('Recipients', [])
                        
                        if sms_recipients:
                            recipient_info = sms_recipients[0]
                            status = recipient_info.get('status', 'Unknown')
                            message_id = recipient_info.get('messageId', '')
                            cost = recipient_info.get('cost', '')
                            
                            # Create log
                            NotificationLog.objects.create(
                                notification=notification,
                                member=member,
                                phone_number=phone_number,
                                status='SENT' if status == 'Success' else 'FAILED',
                                at_message_id=message_id,
                                cost=cost,
                                error_message=None if status == 'Success' else status
                            )
                            
                            if status == 'Success':
                                sent_count += 1
                            else:
                                failed_count += 1
                        else:
                            # No recipient info
                            NotificationLog.objects.create(
                                notification=notification,
                                member=member,
                                phone_number=phone_number,
                                status='FAILED',
                                error_message='No response from SMS service'
                            )
                            failed_count += 1
                    else:
                        # SMS send failed
                        NotificationLog.objects.create(
                            notification=notification,
                            member=member,
                            phone_number=phone_number,
                            status='FAILED',
                            error_message=result.get('error', 'Unknown error')
                        )
                        failed_count += 1
                
                # Update notification
                notification.sms_sent_count = sent_count
                notification.sms_failed_count = failed_count
                notification.sent_at = timezone.now()
                notification.status = 'SENT' if sent_count > 0 else 'FAILED'
                notification.save()
                
                return {
                    'success': True,
                    'sent': sent_count,
                    'failed': failed_count,
                    'total': notification.total_recipients
                }
            else:
                # Just mark as sent without SMS
                notification.status = 'SENT'
                notification.sent_at = timezone.now()
                notification.save()
                
                return {
                    'success': True,
                    'message': 'Notification created without SMS'
                }
                
        except Notification.DoesNotExist:
            return {
                'success': False,
                'error': 'Notification not found'
            }
        except Exception as e:
            if 'notification' in locals():
                notification.status = 'FAILED'
                notification.error_message = str(e)
                notification.save()
            
            return {
                'success': False,
                'error': str(e)
            }
