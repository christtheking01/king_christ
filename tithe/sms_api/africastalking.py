import africastalking
from django.conf import settings
from ..base import BaseSMSProvider


class AfricaTalkingProvider(BaseSMSProvider):
    def __init__(self, username, api_key, sender_id=None):
        africastalking.initialize(username, api_key)
        self.sms = africastalking.SMS
        self.sender_id = sender_id

    def send_sms(self, phone_number, message):
        try:
            # Add prefix to message
            prefixed_message = f"Parokia ya Kristo Mfalme:\n{message}"
            
            params = {
                'message': prefixed_message,
                'recipients': [phone_number]
            }

            if self.sender_id:
                params['sender_id'] = self.sender_id

            response = self.sms.send(**params)

            if response['SMSMessageData']['Recipients']:
                recipient = response['SMSMessageData']['Recipients'][0]
                return {
                    'success': recipient['status'].lower() == 'success',
                    'message_id': recipient.get('messageId'),
                    'data': response,
                    'provider': 'africastalking'
                }
            return {'success': False, 'error': 'No recipients'}
        except Exception as e:
            return {'success': False, 'error': str(e), 'provider': 'africastalking'}

    def send_bulk_sms(self, recipients, message):
        try:
            # Add prefix to message
            prefixed_message = f"Parokia ya Kristo Mfalme:\n{message}"
            
            params = {
                'message': prefixed_message,
                'recipients': recipients
            }

            if self.sender_id:
                params['sender_id'] = self.sender_id

            response = self.sms.send(**params)

            if response['SMSMessageData']['Recipients']:
                results = []
                for recipient in response['SMSMessageData']['Recipients']:
                    results.append({
                        'success': recipient['status'].lower() == 'success',
                        'message_id': recipient.get('messageId'),
                        'phone_number': recipient.get('number'),
                        'status': recipient.get('status'),
                        'cost': recipient.get('cost'),
                        'provider': 'africastalking'
                    })
                return {
                    'success': True,
                    'results': results,
                    'data': response,
                    'provider': 'africastalking'
                }
            return {'success': False, 'error': 'No recipients', 'provider': 'africastalking'}
        except Exception as e:
            return {'success': False, 'error': str(e), 'provider': 'africastalking'}

    def get_balance(self):
        try:
            response = africastalking.Application.get_application_data()
            return {
                'success': True,
                'balance': response.get('balance', '0'),
                'data': response,
                'provider': 'africastalking'
            }
        except Exception as e:
            return {'success': False, 'error': str(e), 'provider': 'africastalking'}


class SMS:
    """
    Singleton SMS class that wraps AfricaTalkingProvider.
    This provides a simple interface for sending SMS messages.
    Usage: from tithe.sms_api.africastalking import SMS
           SMS.send_sms('+255712345678', 'Hello World')
    """
    _instance = None
    _provider = None

    @classmethod
    def _get_provider(cls):
        if cls._provider is None:
            if not getattr(settings, 'SEND_SMS_ENABLED', False):
                raise Exception("SMS sending is disabled. Set SEND_SMS_ENABLED=True to enable.")
            
            username = getattr(settings, 'AFRICASTALKING_USERNAME', '')
            api_key = getattr(settings, 'AFRICASTALKING_API_KEY', '')
            
            if not username or not api_key:
                raise Exception("Africa's Talking credentials not configured. Set AFRICASTALKING_USERNAME and AFRICASTALKING_API_KEY.")
            
            sender_id = getattr(settings, 'AFRICASTALKING_SENDER_ID', None)
            cls._provider = AfricaTalkingProvider(username, api_key, sender_id)
        return cls._provider

    @classmethod
    def send_sms(cls, phone_number, message):
        """
        Send SMS to a single phone number.

        Args:
            phone_number: Phone number in international format (e.g., +255712345678)
            message: Message text to send

        Returns:
            dict: {'success': bool, 'message_id': str, 'data': dict, 'provider': str}
        """
        provider = cls._get_provider()
        return provider.send_sms(phone_number, message)

    @classmethod
    def send_bulk_sms(cls, recipients, message):
        """
        Send SMS to multiple recipients.

        Args:
            recipients: List of phone numbers
            message: Message text to send

        Returns:
            list: List of result dictionaries for each recipient
        """
        provider = cls._get_provider()
        results = []
        for phone in recipients:
            result = provider.send_sms(phone, message)
            results.append(result)
        return results