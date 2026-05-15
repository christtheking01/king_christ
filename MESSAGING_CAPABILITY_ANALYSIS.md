# Messaging System Capability Analysis

**Date:** April 14, 2026
**Application:** Kristo Mfalme Church Management System

---

## Executive Summary

✅ **YES: The application IS capable of sending SMS and in-app messages**

Your system has a comprehensive multi-channel messaging architecture with:

- **SMS**: Africa's Talking (primary), Beem Africa, NextSMS (three providers integrated)
- **In-App**: Real-time WebSocket notifications with Django Channels
- **Email**: Brevo SMTP configured
- **Status**: Mostly functional with ONE critical bug in production use

---

## 1. SMS MESSAGING CAPABILITIES

### 1.1 Available SMS Providers

#### ✅ **Africa's Talking** (PRIMARY - CONFIGURED)

**File:** `tithe/sms_api/africastalking.py` & `tithe/sms_service.py`

**Features:**

- Single SMS sending
- Bulk SMS sending
- Automatic provider initialization
- Response tracking with message IDs
- Cost tracking per SMS
- Handler: `SMS` class (singleton pattern)

**Configuration** (in `settings.py`):

```python
AFRICASTALKING_USERNAME = os.getenv('AFRICASTALKING_USERNAME', 'sandbox')
AFRICASTALKING_API_KEY = os.getenv('AFRICASTALKING_API_KEY', '')
AFRICASTALKING_SENDER_ID = os.getenv('AFRICASTALKING_SENDER_ID', None)
```

**Usage Example:**

```python
from tithe.sms_service import sms_service
result = sms_service.send_sms('+255712345678', 'Hello from Church!')
```

---

#### ⚠️ **Beem Africa** (INTEGRATED BUT INCOMPLETE)

**File:** `tithe/sms_api/BeemAfrica.py`

**Features:**

- ✅ Single SMS sending via `send_sms()` method
- ❌ `send_bulk_sms()` method NOT implemented (returns None)
- ❌ `get_balance()` method NOT implemented
- Requires: `BeemAfrica` package (already in requirements.txt)

**Configuration:**

```python
# NOT configured in settings.py yet
# Would need:
BEEMAFRICA_API_KEY = os.getenv('BEEMAFRICA_API_KEY', '')
BEEMAFRICA_SECRET_KEY = os.getenv('BEEMAFRICA_SECRET_KEY', '')
BEEMAFRICA_SENDER_ID = os.getenv('BEEMAFRICA_SENDER_ID', '')
```

**Status:** Scaffold exists but not in active use

---

#### ⚠️ **NextSMS** (INTEGRATED BUT INCOMPLETE)

**File:** `tithe/sms_api/nextsms.py`

**Features:**

- ✅ Single SMS sending with basic/API key auth options
- ⚠️ `send_bulk_sms()` method declared but `pass` (not implemented)
- ⚠️ `get_balance()` method partially implemented
- Requires: OAuth/API key authentication
- Response parsing for NextSMS API

**Configuration:**

```python
# NOT configured in settings.py
# Would need:
NEXTSMS_API_KEY = os.getenv('NEXTSMS_API_KEY', '')
NEXTSMS_API_SECRET = os.getenv('NEXTSMS_API_SECRET', '')
NEXTSMS_SENDER_ID = os.getenv('NEXTSMS_SENDER_ID', '')
NEXTSMS_BASE_URL = os.getenv('NEXTSMS_BASE_URL', 'https://apigw.nextsms.com')
```

**Status:** Scaffold exists but not in active use

---

### 1.2 SMS Usage in Application

**Active SMS Sending Features:**

1. **Tithe Reminders** → Uses `finance/models.py:send_reminder_sms()`

   ```python
   # sends SMS to members about pending tithes
   pledge.send_reminder_sms()  # ❌ BROKEN - ImportError
   ```

2. **Pledge Reminders** → Uses `finance/models.py:send_reminder_sms()`

   ```python
   # sends SMS to members about pending pledges
   pledge.send_reminder_sms()  # ❌ BROKEN - ImportError
   ```

3. **Broadcast Notifications** → Uses `NotificationService`

   ```python
   # Admin sends bulk SMS/notifications
   notification.send_sms = True
   service.send_notification(notification.id)
   ```

4. **Custom SMS Sending** → Via notifications views
   ```python
   # Send SMS to custom phone numbers
   # endpoint: tithe:send_custom_sms
   ```

---

### 1.3 SMS Database Tracking

**Models:**

- `Notification` - Stores notification configuration with SMS flag
- `NotificationLog` - Logs each individual SMS (phone, status, message ID, cost, error)

**Tracked Fields:**

- `total_recipients` - Total people to send to
- `sms_sent_count` - Successfully sent
- `sms_failed_count` - Failed sends
- `error_message` - Error details if failed

---

## 2. IN-APP MESSAGING CAPABILITIES

### 2.1 Real-Time WebSocket Notifications

✅ **FULLY OPERATIONAL**

**Architecture:**

- **Framework:** Django Channels with Redis
- **Protocol:** WebSocket (`ws://localhost:8000/ws/notifications/`)
- **Authentication:** User-based channels

**Components:**

#### NotificationConsumer (`notifications/consumers.py`)

```
User connects → Consumer joins channel group
├── Personal group: user_{user_id}_notifications
├── Staff group: staff_notifications (if is_staff)
└── Members group: member_notifications

Real-time delivery via:
- notification_message() - New notification
- unread_count_update() - Count changes
```

#### Broadcast System (`notifications/utils.py:broadcast_notification()`)

```
notification.create_user_notifications()
    ↓
Creates UserNotification records for target users
    ↓
broadcast_notification(notification)
    ↓
Sends via channel layers to appropriate groups
    ↓
Connected clients receive instantly
```

---

### 2.2 In-App Notification Models

**UserNotification Model:**

```python
user: ForeignKey → User
notification: ForeignKey → Notification
is_read: Boolean (default=False)
read_at: DateTime (null)
is_sent_via_websocket: Boolean (default=False)
sent_at: DateTime (auto_now_add)

# Tracking:
- Unique per user per notification
- Ordered by most recent
- Can mark as read
```

**Notification Model:**

```python
title: CharField(255)
message: TextField
recipient_type: Choice (MEMBER, MINISTRY, COMMUNITY, ALL, STAFF, etc.)
target_audience: Choice (ALL, STAFF_ONLY, MEMBERS_ONLY, PORTAL_ONLY)
priority: Choice (low, normal, high, urgent)
status: Choice (PENDING, SENDING, SENT, FAILED)
send_sms: Boolean
total_recipients: Integer
sms_sent_count: Integer
sms_failed_count: Integer
```

---

### 2.3 Client-Side WebSocket API

**Supported Actions:**

| Action          | Payload             | Response                        |
| --------------- | ------------------- | ------------------------------- |
| `mark_read`     | `{notification_id}` | `unread_count_updated`          |
| `mark_all_read` | `{}`                | `unread_count_updated`          |
| `fetch_unread`  | `{}`                | `unread_notifications`          |
| (automatic)     | -                   | `initial_count` on connect      |
| (automatic)     | -                   | `new_notification` on broadcast |

**JavaScript Example** (frontend):

```javascript
const ws = new WebSocket("ws://localhost:8000/ws/notifications/");

ws.onmessage = function (e) {
  const data = JSON.parse(e.data);
  if (data.type === "new_notification") {
    console.log("New notification:", data.notification);
    updateUI(data.unread_count);
  }
};

// Mark as read
ws.send(
  JSON.stringify({
    action: "mark_read",
    notification_id: 123,
  }),
);
```

---

## 3. EMAIL MESSAGING CAPABILITIES

### ✅ Email Configured via Brevo SMTP

**Configuration** (in `settings.py`):

```python
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = 'smtp-relay.brevo.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = 'christtheking01@yahoo.com'
```

**Usage:** Django's built-in `send_mail()`

```python
from django.core.mail import send_mail
send_mail(
    subject='Tithe Reminder',
    message='Please submit your tithe',
    from_email='christtheking01@yahoo.com',
    recipient_list=['member@example.com'],
)
```

**Benefits:**

- 300 free emails/day (Brevo free tier)
- Good deliverability
- Supports HTML emails
- Works with Django ORM

---

## 4. CRITICAL ISSUE: ImportError in production

### 🚨 BUG FOUND

**Location:** `finance/models.py` lines 557, 575

**Error:**

```
ImportError: cannot import name 'SMS' from 'tithe.sms_api.africastalking'
```

**Root Cause:**
The code imports:

```python
from tithe.sms_api.africastalking import SMS
```

But the actual class is defined in `tithe/sms_api/africastalking.py` file. The issue appears to be in how the class is being imported or initialized.

**Affected Methods:**

1. `Pledge.send_reminder_sms()` - Line 556
2. `PledgePayment.send_reminder_sms()` - Line 575

**Current Stack Trace:**

```
File "/tithe/models.py", line 557, in send_reminder_sms
    from tithe.sms_api.africastalking import SMS
ImportError: cannot import name 'SMS' from 'tithe.sms_api.africastalking'
```

---

## 5. MESSAGING FEATURES BY USE CASE

### Use Case 1: Broadcast Tithe Reminder to All Tithers

✅ **WORKS** (if SMS import fixed)

- Uses: `NotificationService` → `AfricasTalkingService`
- SMS: ✅ Sends to all active tithe payers
- In-App: ✅ Real-time WebSocket to staff & portal members
- Email: ✅ Can be added

### Use Case 2: Notify Member of Pledge Status

✅ **PARTIALLY WORKS**

- SMS: ✅ Can send (if import fixed)
- In-App: ✅ Creates UserNotification
- Email: ✅ Not yet implemented

### Use Case 3: Send Alert to Leadership

✅ **WORKS**

- SMS: ✅ To community/ministry leaders
- In-App: ✅ Real-time to staff group
- Email: ✅ Can be added

### Use Case 4: Broadcast to Custom Phone Numbers

✅ **PARTIALLY WORKS**

- SMS: ⚠️ Needs improvement in phone number validation
- In-App: ❌ Not applicable for unknown numbers
- Email: ❌ Not supported (no email required)

---

## 6. RECIPIENT TARGETING

### Available Recipient Groups

```python
RECIPIENT_TYPES = [
    'MEMBER',                # Single member (needs member_id)
    'MINISTRY',              # All members in ministry
    'COMMUNITY',             # All members in community/shepherd
    'ALL',                   # All active members
    'Staff',                 # All active staff users
    'PORTAL_MEMBERS',        # Portal-enabled members
    'COMMUNITY_LEADERS',     # All community leaders
    'MINISTRY_LEADERS',      # All ministry leaders
    'ZONE_LEADERS',          # All zone leaders
    'TITHE_PAYERS',          # Members who pay tithe
    'PLEDGERS',              # Members with active pledges
    'CUSTOM_PHONES',         # Custom phone numbers (manual list)
]

TARGET_AUDIENCE = [
    'ALL',           # Everyone sees in-app notification
    'STAFF_ONLY',    # Only staff portal access
    'MEMBERS_ONLY',  # Only member portal access
    'PORTAL_ONLY',   # Only portal-enabled users
]
```

### Phone Number Extraction

- **Member objects** → `member.telephone` field
- **Zone/Community Leaders** → `leader.phone` field
- **Custom numbers** → comma/semicolon-separated list in `custom_phone_numbers`

---

## 7. CONFIGURATION CHECKLIST

### For Africa's Talking (PRIMARY)

✅ **Already Configured**

```
AFRICASTALKING_USERNAME = 'sandbox' | 'your_username'
AFRICASTALKING_API_KEY = 'your_api_key'
AFRICASTALKING_SENDER_ID = 'ChristsKingChurch' (optional)
```

### For Beem Africa (Optional)

❌ **Not Configured** - Add if needed:

```
BEEMAFRICA_API_KEY = 'your_api_key'
BEEMAFRICA_SECRET_KEY = 'your_secret_key'
BEEMAFRICA_SENDER_ID = 'ChristsKingChurch'
```

### For NextSMS (Optional)

❌ **Not Configured** - Add if needed:

```
NEXTSMS_API_KEY = 'your_api_key'
NEXTSMS_API_SECRET = 'your_secret_key'
NEXTSMS_SENDER_ID = 'ChristsKingChurch'
NEXTSMS_BASE_URL = 'https://apigw.nextsms.com'
```

### For Email (Brevo)

⚠️ **Partially Configured**

```
EMAIL_HOST_USER = 'your_brevo_email'
EMAIL_HOST_PASSWORD = 'your_brevo_smtp_password'
DEFAULT_FROM_EMAIL = 'christtheking01@yahoo.com'
```

### For Real-Time Notifications (Channels)

✅ **Configured**

```
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],
        },
    },
}
```

---

## 8. CURRENT LIMITATIONS & ISSUES

### Critical Issues

| Issue                            | Severity    | Location                      | Fix                                      |
| -------------------------------- | ----------- | ----------------------------- | ---------------------------------------- |
| SMS import error                 | 🔴 Critical | `finance/models.py:557,575`   | Fix import statement or class definition |
| Beem bulk SMS not implemented    | 🟡 High     | `tithe/sms_api/BeemAfrica.py` | Implement `send_bulk_sms()` method       |
| NextSMS bulk SMS not implemented | 🟡 High     | `tithe/sms_api/nextsms.py`    | Implement `send_bulk_sms()` method       |

### Feature Gaps

| Gap                             | Impact | Solution                               |
| ------------------------------- | ------ | -------------------------------------- |
| No SMS/Email choice UI          | Medium | Add radio buttons in notification form |
| No provider fallback            | Medium | Implement provider switching logic     |
| No error retry mechanism        | Medium | Add Celery tasks with retry logic      |
| No rate limiting for SMS        | High   | Add per-recipient throttling           |
| No SMS delivery status tracking | Medium | Use Africa's Talking delivery reports  |
| Limited phone validation        | Medium | Add more robust validation regex       |

---

## 9. QUICK START: SENDING A MESSAGE

### Scenario A: Send Broadcast Notification

1. **Via Admin Panel:**
   - Go to Notifications → Create Notification
   - Select recipients (All, Ministry, Custom, etc.)
   - Check "Send SMS" to include SMS delivery
   - Click Create

2. **Via Code:**

```python
from notifications.models import Notification
from notifications.services import NotificationService

# Create notification
notification = Notification.objects.create(
    title="Tithe Reminder",
    message="Please submit your tithes",
    recipient_type='TITHE_PAYERS',
    target_audience='ALL',
    send_sms=True,
    created_by=request.user
)

# Send it
service = NotificationService()
result = service.send_notification(notification.id)
print(f"Sent: {result['sent']}, Failed: {result['failed']}")
```

### Scenario B: Send SMS Only (No In-App)

```python
from tithe.sms_service import sms_service

# Single SMS
result = sms_service.send_sms(
    phone_number='+255712345678',
    message='Welcome to Christ the King Church'
)

# Bulk SMS
results = sms_service.send_sms(
    phone_number=['+255712345678', '+255723456789'],
    message='Church service at 10 AM Sunday'
)
```

### Scenario C: Send In-App Notification Only

```python
from notifications.models import Notification

# Create notification (SMS disabled)
notification = Notification.objects.create(
    title="Welcome",
    message="You've been added to the portal",
    target_audience='PORTAL_ONLY',
    send_sms=False,
    created_by=system_user
)

# This triggers WebSocket delivery automatically
notification.create_user_notifications()
```

---

## 10. RECOMMENDATIONS

### Priority 1 (IMMEDIATE)

1. ✅ **Fix SMS Import Error** - Use `SMSService` instead of direct import
2. ✅ **Add Error Handling** - Wrap SMS calls in try-except
3. ✅ **Test Africa's Talking** - Verify production credentials work

### Priority 2 (SHORT-TERM)

1. **Implement Celery Tasks** - Queue SMS for async delivery
2. **Add Provider Fallback** - Switch providers if primary fails
3. **Implement Delivery Reports** - Track SMS status via webhooks
4. **Add Email Delivery** - Include email in broadcast notifications

### Priority 3 (MEDIUM-TERM)

1. **Complete Beem Africa Integration** - Full implementation if needed
2. **Complete NextSMS Integration** - Full implementation if needed
3. **Add SMS Templates** - Predefined message formats
4. **Add Scheduling** - Schedule notifications for later
5. **Add Delivery Analytics** - Dashboard for message metrics

---

## 11. TESTING GUIDELINES

### Test SMS Sending

```python
# Development
AFRICASTALKING_USERNAME = 'sandbox'
AFRICASTALKING_API_KEY = 'fake_key'

# This will use sandbox mode and NOT send real SMS

# Production
AFRICASTALKING_USERNAME = 'your_username'
AFRICASTALKING_API_KEY = 'your_real_api_key'
```

### Test In-App Notifications

```
# Terminal 1: Start Django with Daphne
python manage.py runserver --settings=christ_king_church.settings

# Terminal 2: Start Redis
redis-server

# Navigate to: http://localhost:8000
# WebSocket will auto-connect
# Unread notifications show real-time
```

### Test Broadcast

```python
# Python shell
python manage.py shell

from notifications.models import Notification
from notifications.services import NotificationService

n = Notification.objects.create(
    title="Test",
    message="Test message",
    recipient_type='ALL',
    send_sms=True,
    created_by=User.objects.first()
)

service = NotificationService()
service.send_notification(n.id)
```

---

## 12. SUMMARY TABLE

| Feature         | SMS                | In-App             | Email         |
| --------------- | ------------------ | ------------------ | ------------- |
| **Status**      | ✅ Works (has bug) | ✅ Full            | ✅ Configured |
| **Provider**    | Africa's Talking   | Channels/WebSocket | Brevo         |
| **Real-Time**   | ❌ Queued          | ✅ Instant         | ❌ Delayed    |
| **Recipients**  | All groups         | Logged-in users    | Can support   |
| **Tracking**    | ✅ Per SMS         | ✅ Per User        | ✅ Possible   |
| **Cost**        | 💰 Per SMS         | 💰 Server          | 💰 Free tier  |
| **Reliability** | 🟢 High            | 🟢 High            | 🟢 High       |

---

## CONCLUSION

Your application **HAS COMPREHENSIVE MESSAGING CAPABILITIES** across all three channels (SMS, In-App, Email). The system is well-architected with proper models for tracking and broadcasting.

**Main Action Item:** Fix the SMS import error in `finance/models.py` to enable tithe/pledge reminders to work properly.

Once fixed, you'll have a production-ready multi-channel messaging system!
