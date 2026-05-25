from django.utils import timezone
import logging
from django.conf import settings
import africastalking

logger = logging.getLogger(__name__)

_at_sms = None


class NotificationService:
    """Service class for handling notifications"""

    def __init__(self):
        self.sms_service = SMS()

    def send_email(self, to, subject, message, template=None, context=None, from_email=None):
        """
        Send email using Brevo API v3 (more reliable than SMTP).

        Args:
            to: Recipient email address (string or list)
            subject: Email subject
            message: Plain text message
            template: Optional HTML template path for HTML version
            context: Optional dict for template rendering
            from_email: Optional sender email

        Returns:
            bool: True if sent successfully, False otherwise
        """
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        from utils.brevo_email import send_email_via_brevo
        import logging

        logger = logging.getLogger(__name__)

        try:
            # Prepare email content
            if template and context:
                html_content = render_to_string(template, context)
                text_content = strip_tags(html_content)
            else:
                html_content = None
                text_content = message

            # Send using Brevo
            result = send_email_via_brevo(
                to=to,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                from_email=from_email
            )

            if result:
                logger.info(f"Email sent successfully to {to}")
                return True
            else:
                logger.error(f"Failed to send email to {to}")
                return False

        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False

    def send_sms(self, phone_number, message):
        """
        Send SMS using the SMS service.
        
        Args:
            phone_number: Phone number in international format
            message: SMS message content
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            if self.sms_service:
                result = self.sms_service.send_sms(phone_number, message)
                return result.get('status', 'error') == 'success'
            else:
                logger.warning("SMS service not available")
                return False
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}")
            return False

    def _normalize_phone(self, phone: str) -> str:
        """
        Normalize phone number to international format.
        Handles Tanzanian numbers by default (+255).
        """
        phone = phone.strip()
        if phone.startswith('0'):
            return '+255' + phone[1:]
        elif not phone.startswith('+'):
            return '+255' + phone
        return phone

    def send_notification(self, notification_id):
        """
        Send notification via SMS.

        Args:
            notification_id: ID of the notification to send

        Returns:
            dict: Status of the operation
        """
        from .models import Notification, NotificationLog
        
        try:
            notification = Notification.objects.get(id=notification_id)

            # Update status to SENDING
            notification.status = 'SENDING'
            notification.save()

            # Get recipients
            recipients = notification.get_recipients()

            # Handle both QuerySet and list returns
            if hasattr(recipients, 'count') and hasattr(recipients, 'model'):
                notification.total_recipients = recipients.count()
                has_recipients = recipients.exists()
            else:
                notification.total_recipients = len(recipients) if recipients else 0
                has_recipients = bool(recipients)
            notification.save()

            if not has_recipients:
                notification.status = 'FAILED'
                notification.error_message = 'No recipients found'
                notification.save()
                return {'success': False, 'error': 'No recipients found'}

            # Send SMS if enabled
            if notification.send_sms:
                sent_count = 0
                failed_count = 0

                # Handle custom phone numbers separately
                if notification.recipient_type == 'CUSTOM_PHONES':
                    phone_numbers = notification.get_phone_numbers()
                    for phone_number in phone_numbers:
                        # Normalize to international format
                        normalized_phone = self._normalize_phone(phone_number)

                        result = self.sms_service.send_sms(
                            phone_number=normalized_phone,
                            message=notification.message
                        )

                        if result['success']:
                            message_id = result.get('message_id', '')
                            response_data = result.get('data', {})
                            sms_recipients = response_data.get('SMSMessageData', {}).get('Recipients', [])

                            if sms_recipients:
                                recipient_info = sms_recipients[0]
                                status = recipient_info.get('status', 'Unknown')
                                cost = recipient_info.get('cost', '')
                                is_sent = status.lower() in ('success', 'sent')

                                NotificationLog.objects.create(
                                    notification=notification,
                                    member=None,
                                    phone_number=normalized_phone,
                                    status='SENT' if is_sent else 'FAILED',
                                    at_message_id=message_id,
                                    cost=cost,
                                    error_message=None if is_sent else status
                                )

                                if is_sent:
                                    sent_count += 1
                                else:
                                    failed_count += 1
                            else:
                                NotificationLog.objects.create(
                                    notification=notification,
                                    member=None,
                                    phone_number=normalized_phone,
                                    status='SENT',
                                    at_message_id=message_id,
                                    cost='',
                                    error_message=None
                                )
                                sent_count += 1
                        else:
                            NotificationLog.objects.create(
                                notification=notification,
                                member=None,
                                phone_number=normalized_phone,
                                status='FAILED',
                                error_message=result.get('error', 'Unknown error')
                            )
                            failed_count += 1
                else:
                    # Handle member-based recipients
                    for member in recipients:
                        if not member.telephone:
                            NotificationLog.objects.create(
                                notification=notification,
                                member=member,
                                phone_number='N/A',
                                status='FAILED',
                                error_message='No phone number'
                            )
                            failed_count += 1
                            continue

                        # Normalize to international format
                        phone_number = self._normalize_phone(str(member.telephone))

                        result = self.sms_service.send_sms(
                            phone_number=phone_number,
                            message=notification.message
                        )

                        if result['success']:
                            message_id = result.get('message_id', '')
                            response_data = result.get('data', {})
                            sms_recipients = response_data.get('SMSMessageData', {}).get('Recipients', [])

                            if sms_recipients:
                                recipient_info = sms_recipients[0]
                                status = recipient_info.get('status', 'Unknown')
                                cost = recipient_info.get('cost', '')
                                is_sent = status.lower() in ('success', 'sent')

                                NotificationLog.objects.create(
                                    notification=notification,
                                    member=member,
                                    phone_number=phone_number,
                                    status='SENT' if is_sent else 'FAILED',
                                    at_message_id=message_id,
                                    cost=cost,
                                    error_message=None if is_sent else status
                                )

                                if is_sent:
                                    sent_count += 1
                                else:
                                    failed_count += 1
                            else:
                                NotificationLog.objects.create(
                                    notification=notification,
                                    member=member,
                                    phone_number=phone_number,
                                    status='SENT',
                                    at_message_id=message_id,
                                    cost='',
                                    error_message=None
                                )
                                sent_count += 1
                        else:
                            NotificationLog.objects.create(
                                notification=notification,
                                member=member,
                                phone_number=phone_number,
                                status='FAILED',
                                error_message=result.get('error', 'Unknown error')
                            )
                            failed_count += 1

                # Update notification counts and status
                notification.sms_sent_count = sent_count
                notification.sms_failed_count = failed_count
                notification.sent_at = timezone.now()
                notification.status = 'SENT' if sent_count > 0 else 'FAILED'
                notification.save()

                # Create user notifications for real-time delivery
                try:
                    notification.create_user_notifications()
                except Exception as e:
                    logger.error(f"Error creating user notifications: {e}")

                return {
                    'success': True,
                    'sent': sent_count,
                    'failed': failed_count,
                    'total': notification.total_recipients
                }

            else:
                # Mark as sent without SMS
                notification.status = 'SENT'
                notification.sent_at = timezone.now()
                notification.save()

                try:
                    notification.create_user_notifications()
                except Exception as e:
                    logger.error(f"Error creating user notifications: {e}")

                return {
                    'success': True,
                    'message': 'Notification created without SMS'
                }

        except Notification.DoesNotExist:
            return {'success': False, 'error': 'Notification not found'}

        except Exception as e:
            if 'notification' in locals():
                notification.status = 'FAILED'
                notification.error_message = str(e)
                notification.save()
            logger.exception(f"Unexpected error in send_notification: {e}")
            return {'success': False, 'error': str(e)}


def _get_sms_client():
    """Lazy initialization of Africa's Talking SMS client"""
    global _at_sms
    if _at_sms is None:
        if not getattr(settings, 'SEND_SMS_ENABLED', False):
            logger.warning("SMS sending is disabled. Set SEND_SMS_ENABLED=True to enable.")
            return None

        username = getattr(settings, 'AFRICASTALKING_USERNAME', '').strip()
        api_key = getattr(settings, 'AFRICASTALKING_API_KEY', '').strip()

        if not username or not api_key:
            logger.error(
                "Africa's Talking credentials not configured. "
                "Set AFRICASTALKING_USERNAME and AFRICASTALKING_API_KEY."
            )
            return None

        try:
            africastalking.initialize(username, api_key)
            _at_sms = africastalking.SMS
            logger.info("Africa's Talking SMS client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Africa's Talking: {e}")
            return None

    return _at_sms


class SMS:
    """Africa's Talking SMS wrapper"""

    def send_sms(self, phone_number: str, message: str) -> dict:
        """
        Send an SMS via Africa's Talking.

        Args:
            phone_number: Recipient in international format e.g. +255712345678
            message: Message body

        Returns:
            dict with keys: success (bool), message_id, provider, data, error
        """
        if not getattr(settings, 'SEND_SMS_ENABLED', False):
            logger.warning("SMS sending is disabled. Set SEND_SMS_ENABLED=True to enable.")
            return {
                'success': False,
                'error': 'SMS sending is disabled',
                'provider': 'africastalking'
            }

        if not phone_number or not phone_number.startswith('+'):
            logger.error(f"Invalid phone format: {phone_number}. Must start with +")
            return {
                'success': False,
                'error': 'Phone number must be in international format (e.g., +255...)',
                'provider': 'africastalking'
            }

        at_sms = _get_sms_client()
        if at_sms is None:
            return {
                'success': False,
                'error': 'SMS client not initialized. Check credentials and SEND_SMS_ENABLED setting.',
                'provider': 'africastalking'
            }

        sender_id = getattr(settings, 'AFRICASTALKING_SENDER_ID', None)

        try:
            prefixed_message = f"Parokia ya Kristo Mfalme:\n{message}"

            params = {
                'message': prefixed_message,
                'recipients': [phone_number]
            }
            if sender_id:
                params['sender_id'] = sender_id

            response = at_sms.send(**params)
            recipients = response.get('SMSMessageData', {}).get('Recipients', [])

            if recipients:
                recipient_info = recipients[0]
                status = recipient_info.get('status', 'unknown')
                msg_id = recipient_info.get('messageId', 'no_id')
                is_success = status.lower() in ('success', 'sent')  # handle both statuses

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

            logger.warning("AT SMS: No recipient data returned for %s", phone_number)
            return {
                'success': False,
                'error': 'No recipient data returned',
                'provider': 'africastalking'
            }

        except Exception as e:
            logger.exception("Africa's Talking SDK Error")
            return {
                'success': False,
                'error': str(e),
                'provider': 'africastalking'
            }