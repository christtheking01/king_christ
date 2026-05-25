import logging
from django.conf import settings
from django.utils import timezone
from .models import Notification, NotificationLog
from tithe.sms_api.africastalking import SMS

logger = logging.getLogger(__name__)


class NotificationService:
    """Service class for handling notifications"""

    def __init__(self):
        self.sms_service = SMS()  # Fix: instantiate, not assign the class

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

        try:
            # Ensure 'to' is a single email
            if isinstance(to, list):
                to = to[0] if to else None
            if not to:
                logger.error("No recipient email provided")
                return False

            # Prepare HTML content if template provided
            html_content = None
            if template:
                try:
                    html_content = render_to_string(template, context or {})
                    message = strip_tags(html_content)  # Plain text fallback
                except Exception as e:
                    logger.warning(f"Template render failed: {e}")

            # Use Brevo API
            success, message_id, error = send_email_via_brevo(
                to_email=to,
                subject=subject,
                html_content=html_content,
                text_content=message,
                from_email=from_email
            )

            if success:
                logger.info(f"Email sent to {to} via Brevo API, messageId: {message_id}")
                return True
            else:
                logger.error(f"Brevo API failed to send to {to}: {error}")
                return False

        except Exception as e:
            logger.error(f"Email failed to {to}: {e}")
            return False

    def send_notification(self, notification_id):
        """
        Send notification via SMS.

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
                    logger.error(f"Error creating user notifications: {e}", exc_info=True)

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
                    logger.error(f"Error creating user notifications: {e}", exc_info=True)

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