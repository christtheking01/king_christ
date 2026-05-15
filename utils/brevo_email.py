"""Brevo (Sendinblue) API v3 email service - More reliable than SMTP"""
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def send_email_via_brevo(to_email, subject, html_content=None, text_content=None, 
                         from_email=None, from_name=None):
    """
    Send email using Brevo API v3 (more reliable than SMTP)
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML version of the email
        text_content: Plain text version (optional)
        from_email: Sender email (defaults to DEFAULT_FROM_EMAIL)
        from_name: Sender name (optional)
    
    Returns:
        tuple: (success: bool, message_id: str or None, error: str or None)
    """
    # Get Brevo API key from settings
    api_key = getattr(settings, 'BREVO_API_KEY', None)
    
    if not api_key:
        # Try to get from environment directly
        import os
        api_key = os.getenv('BREVO_API_KEY')
    
    if not api_key:
        logger.error("BREVO_API_KEY not configured")
        return False, None, "BREVO_API_KEY not configured"
    
    # Set defaults
    if from_email is None:
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@christtheking.space')
    
    if from_name is None:
        from_name = "Christ The King Parish"
    
    # Prepare headers
    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json"
    }
    
    # Prepare payload
    payload = {
        "sender": {
            "name": from_name,
            "email": from_email
        },
        "to": [
            {
                "email": to_email
            }
        ],
        "subject": subject
    }
    
    # Add content
    if html_content:
        payload["htmlContent"] = html_content
    
    if text_content:
        payload["textContent"] = text_content
    elif not html_content:
        # Must have at least one content type
        payload["textContent"] = ""
    
    try:
        logger.info(f"Sending email via Brevo API to {to_email}")
        logger.debug(f"From: {from_email}, Subject: {subject}")
        
        response = requests.post(
            BREVO_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 201:
            # Success
            result = response.json()
            message_id = result.get('messageId')
            logger.info(f"Email sent successfully to {to_email}, messageId: {message_id}")
            return True, message_id, None
        else:
            # Error
            error_msg = f"Brevo API error: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return False, None, error_msg
            
    except requests.exceptions.Timeout:
        error_msg = "Brevo API request timed out"
        logger.error(error_msg)
        return False, None, error_msg
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Brevo API request failed: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg


def send_verification_email_brevo(email, full_name, code):
    """
    Send verification email using Brevo API
    
    Args:
        email: Recipient email
        full_name: User's full name
        code: Verification code
    
    Returns:
        bool: True if sent successfully, False otherwise
    """
    subject = "Christ The King Parish - Verification Code"
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #2c5aa0;">Christ The King Parish</h2>
        <p>Hello <strong>{full_name}</strong>,</p>
        <p>Your verification code for the Christ The King Parish Member Portal is:</p>
        <div style="background: #f4f4f4; padding: 20px; text-align: center; margin: 20px 0;">
            <span style="font-size: 32px; font-weight: bold; color: #2c5aa0; letter-spacing: 5px;">{code}</span>
        </div>
        <p>This code will expire in <strong>30 minutes</strong>.</p>
        <p>If you did not request this code, please ignore this email.</p>
        <hr style="margin-top: 30px; border: none; border-top: 1px solid #ddd;">
        <p style="color: #666; font-size: 12px;">
            God bless you,<br>
            <strong>Christ The King Parish</strong>
        </p>
    </body>
    </html>
    """
    
    text_content = f"""Hello {full_name},

Your verification code for Christ The King Parish Member Portal is: {code}

This code will expire in 30 minutes.

If you did not request this code, please ignore this email.

God bless you,
Christ The King Parish"""
    
    success, message_id, error = send_email_via_brevo(
        to_email=email,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )
    
    return success
