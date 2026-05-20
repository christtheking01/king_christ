# Messaging Implementation Guide

**Quick Reference for Using SMS, In-App, and Email Messaging**

---

## QUICK REFERENCE

### Send SMS Only

```python
from tithe.sms_service import sms_service

# Single recipient
result = sms_service.send_sms('+255712345678', 'Hello Member!')

# Check result
if result['success']:
    print(f"SMS sent: {result['message_id']}")
else:
    print(f"Failed: {result['error']}")
```

### Send In-App Notification

```python
from notifications.models import Notification

notification = Notification.objects.create(
    title="Welcome",
    message="You've been registered",
    target_audience='ALL',
    send_sms=False,  # SMS disabled
    created_by=request.user
)

# Automatically delivers via WebSocket to connected users
notification.create_user_notifications()
```

### Send SMS + In-App Notification

```python
from notifications.models import Notification
from notifications.services import NotificationService

# Create notification
notification = Notification.objects.create(
    title="Tithe Reminder",
    message="Please submit your tithe",
    recipient_type='TITHE_PAYERS',
    target_audience='ALL',
    send_sms=True,
    created_by=request.user
)

# Send SMS + create in-app notifications
service = NotificationService()
result = service.send_notification(notification.id)
print(f"Sent: {result['sent']}, Failed: {result['failed']}")
```

### Send Email

```python
from django.core.mail import send_mail

send_mail(
    subject='Welcome to Church Portal',
    message='Thank you for joining our community',
    from_email='christtheking01@yahoo.com',
    recipient_list=['member@example.com'],
    html_message='<h1>Welcome!</h1><p>Thank you for joining</p>'
)
```

---

## RECIPIENT TARGETING EXAMPLES

### Example 1: Notify All Ministry Members

```python
notification = Notification.objects.create(
    title="Youth Ministry Meeting",
    message="Youth meeting this Sunday at 5 PM",
    recipient_type='MINISTRY',
    ministry=youth_ministry,
    target_audience='ALL',
    send_sms=True,
    created_by=request.user
)
```

### Example 2: Notify Specific Community

```python
notification = Notification.objects.create(
    title="Community Service",
    message="Community service at 10 AM",
    recipient_type='COMMUNITY',
    community=community_obj,
    target_audience='ALL',
    send_sms=True,
    created_by=request.user
)
```

### Example 3: Notify Only Leadership

```python
notification = Notification.objects.create(
    title="Leadership Meeting",
    message="Leadership meeting tomorrow at 6 PM",
    recipient_type='ZONE_LEADERS',
    target_audience='STAFF_ONLY',  # Only staff see in-app
    send_sms=True,
    created_by=request.user
)
```

### Example 4: Notify Custom Phone Numbers

```python
notification = Notification.objects.create(
    title="Announcement",
    message="Important announcement",
    recipient_type='CUSTOM_PHONES',
    custom_phone_numbers='+255712345678,+255723456789,+255734567890',
    target_audience='ALL',
    send_sms=True,
    created_by=request.user
)
```

### Example 5: Tithe Payers Only

```python
notification = Notification.objects.create(
    title="Tithe Thank You",
    message="Thank you for your tithe support",
    recipient_type='TITHE_PAYERS',
    target_audience='MEMBERS_ONLY',
    send_sms=True,
    created_by=request.user
)
```

---

## PHONE NUMBER HANDLING

### Valid Phone Formats

```python
# International format (required)
'+255712345678'      # ✅ Correct
'+255723456789'      # ✅ Correct

# Invalid formats (will be rejected)
'0712345678'         # ❌ Missing country code
'255712345678'       # ❌ Missing + sign
'712345678'          # ❌ Too short
```

### Auto-Format Helper

```python
from notifications.utils import format_phone_for_kenya

# Returns formatted phone number (Tanzania format)
phone = format_phone_for_kenya('0712345678')  # Returns '+255712345678'
phone = format_phone_for_kenya('255712345678') # Returns '+255712345678'
phone = format_phone_for_kenya('+255712345678') # Returns '+255712345678'
```

---

## NOTIFICATION TRACKING

### Get Recipients of Notification

```python
notification = Notification.objects.get(id=1)

# Get all recipients
recipients = notification.get_recipients()
print(f"Total recipients: {recipients.count()}")

# Get phone numbers
phones = notification.get_phone_numbers()
print(f"Valid phones: {len(phones)}")

# List recipient details
for recipient in recipients[:10]:
    print(f"{recipient.name}: {recipient.telephone}")
```

### Get SMS Logs

```python
notification = Notification.objects.get(id=1)

# View SMS logs
logs = notification.logs.all()

for log in logs:
    print(f"""
    Recipient: {log.member.name}
    Phone: {log.phone_number}
    Status: {log.status}
    Message ID: {log.at_message_id}
    Cost: {log.cost}
    Error: {log.error_message}
    """)

# Filter by status
successful = notification.logs.filter(status='SENT')
failed = notification.logs.filter(status='FAILED')

print(f"Sent: {successful.count()}, Failed: {failed.count()}")
```

### Get Read Status (In-App)

```python
notification = Notification.objects.get(id=1)

# Who has read this?
read_status = notification.read_status.all()
for status in read_status:
    print(f"{status.user.username} read on {status.read_at}")

# Who hasn't read yet?
unread = notification.user_notifications.filter(is_read=False)
print(f"Still unread by {unread.count()} users")
```

---

## ERROR HANDLING

### Handling SMS Failures

```python
from tithe.sms_service import sms_service
import logging

logger = logging.getLogger(__name__)

try:
    result = sms_service.send_sms('+255712345678', 'Test')

    if not result['success']:
        logger.error(f"SMS failed: {result['error']}")
        # Handle failure (retry, notify admin, etc.)
    else:
        logger.info(f"SMS sent: {result['message_id']}")

except Exception as e:
    logger.exception(f"Unexpected error sending SMS: {e}")
```

### Handling In-App Notification Failures

```python
from notifications.models import Notification
from notifications.services import NotificationService

try:
    notification = Notification.objects.create(
        title="Test",
        message="Test message",
        target_audience='ALL',
        created_by=request.user
    )

    service = NotificationService()
    result = service.send_notification(notification.id)

    if result['success']:
        print(f"Sent to {result['sent']} users")
        if result['failed'] > 0:
            print(f"Failed for {result['failed']} users")
    else:
        print(f"Error: {result['error']}")
        # Log and notify admin

except Exception as e:
    logger.exception(f"Error sending notification: {e}")
```

---

## CELERY TASKS (For Background Processing)

### Queue SMS for Async Delivery

```python
# In tasks.py
from celery import shared_task
from tithe.sms_service import sms_service

@shared_task
def send_sms_async(phone_numbers, message):
    """Send SMS asynchronously"""
    results = []
    for phone in phone_numbers:
        result = sms_service.send_sms(phone, message)
        results.append(result)
    return results

# Usage
send_sms_async.delay(['+255712345678', '+255723456789'], 'Hello Members!')
```

### Queue Notification for Async Delivery

```python
@shared_task
def send_notification_async(notification_id):
    """Send notification asynchronously"""
    from notifications.models import Notification
    from notifications.services import NotificationService

    notification = Notification.objects.get(id=notification_id)
    service = NotificationService()
    return service.send_notification(notification.id)

# Usage
send_notification_async.delay(notification.id)
```

---

## WEBSOKET CLIENT EXAMPLE

### JavaScript Frontend

```javascript
// Connect to WebSocket
const ws = new WebSocket("ws://" + window.location.host + "/ws/notifications/");

ws.onopen = function () {
  console.log("Connected to notification server");
};

ws.onmessage = function (e) {
  const data = JSON.parse(e.data);

  if (data.type === "initial_count") {
    // Update unread badge
    document.getElementById("unread-badge").textContent = data.unread_count;
  } else if (data.type === "new_notification") {
    // Display new notification
    showNotification(data.notification);
    updateUnreadCount(data.unread_count);
  } else if (data.type === "unread_count_updated") {
    // Update unread count
    document.getElementById("unread-badge").textContent = data.unread_count;
  }
};

// Mark notification as read
function markAsRead(notificationId) {
  ws.send(
    JSON.stringify({
      action: "mark_read",
      notification_id: notificationId,
    }),
  );
}

// Mark all as read
function markAllAsRead() {
  ws.send(
    JSON.stringify({
      action: "mark_all_read",
    }),
  );
}

// Fetch unread notifications
function fetchUnread() {
  ws.send(
    JSON.stringify({
      action: "fetch_unread",
    }),
  );
}

ws.onerror = function () {
  console.error("WebSocket error");
};

ws.onclose = function () {
  console.log("Disconnected from notification server");
  // Attempt reconnect after 5 seconds
  setTimeout(function () {
    location.reload();
  }, 5000);
};
```

---

## ENVIRONMENT VARIABLES

### Required for SMS (Africa's Talking)

```bash
AFRICASTALKING_USERNAME=your_username
AFRICASTALKING_API_KEY=your_api_key
AFRICASTALKING_SENDER_ID=ChristsKingChurch
```

### Required for Email (Brevo)

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_brevo_email
EMAIL_HOST_PASSWORD=your_brevo_password
DEFAULT_FROM_EMAIL=christtheking01@yahoo.com
```

### Required for Real-Time (Redis)

```bash
REDIS_URL=redis://localhost:6379/0
# or individual settings:
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
```

---

## TESTING

### Test SMS Service

```python
from tithe.sms_service import sms_service

# Test single SMS
result = sms_service.send_sms('+255712345678', 'Test from Django')
print(result)

# Output: {'success': True, 'message_id': '...', 'provider': 'africastalking', 'data': {...}}
```

### Test Notification Creation

```python
from notifications.models import Notification
from django.contrib.auth.models import User

user = User.objects.first()

notification = Notification.objects.create(
    title="Test Notification",
    message="This is a test notification",
    recipient_type='ALL',
    target_audience='STAFF_ONLY',
    send_sms=False,
    created_by=user
)

notification.create_user_notifications()
print(f"Created {notification.user_notifications.count()} user notifications")
```

### Test WebSocket Connection

```
# Browser console
const ws = new WebSocket('ws://localhost:8000/ws/notifications/');
ws.onopen = () => console.log('Connected');
ws.onmessage = (e) => console.log(e.data);
```

---

## COMMON ISSUES & FIXES

### Issue: SMS not sending

**Solution:**

```python
# Check credentials
from django.conf import settings
print(f"Username: {settings.AFRICASTALKING_USERNAME}")
print(f"API Key configured: {bool(settings.AFRICASTALKING_API_KEY)}")

# Test connection
from tithe.sms_service import sms_service
result = sms_service.send_sms('+255712345678', 'Test')
if not result['success']:
    print(f"Error: {result['error']}")
```

### Issue: In-App notifications not appearing

**Solution:**

```python
# Check WebSocket connection
# Browser console: ws.readyState === 1 means connected

# Check Redis
redis-cli ping  # Should return PONG

# Check channel layer
django-admin shell_plus
>>> from channels.layers import get_channel_layer
>>> channel_layer = get_channel_layer()
>>> import asyncio
>>> asyncio.run(channel_layer.send('test', {"type": "test"}))
```

### Issue: Phone numbers not valid

**Solution:**

```python
# Use format helper
from notifications.utils import format_phone_for_kenya

phone = format_phone_for_kenya('0712345678')
print(phone)  # Should print: +255712345678

# Or validate manually
if phone.startswith('+255') and len(phone) in [12, 13]:
    print("Valid")
```

---

## MONITORING & LOGGING

### Check SMS Delivery Status

```python
from notifications.models import NotificationLog

# Recent SMS
logs = NotificationLog.objects.order_by('-created_at')[:50]

# Failed SMS
failed = NotificationLog.objects.filter(status='FAILED')
for log in failed:
    print(f"{log.member.name}: {log.error_message}")

# SMS costs
total = NotificationLog.objects.filter(status='SENT').count()
print(f"Total SMS sent: {total}")
```

### Check Notification Tracking

```python
from notifications.models import UserNotification

# Unread by user
unread_count = UserNotification.objects.filter(
    user=request.user,
    is_read=False
).count()

# Read time tracking
read_times = UserNotification.objects.filter(
    user=request.user,
    is_read=True
).order_by('-read_at')
```

---

**For more detailed information, see:
`MESSAGING_CAPABILITY_ANALYSIS.md`**
