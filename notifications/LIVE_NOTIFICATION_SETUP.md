# Live Notification System Setup Guide

## Overview

The notification system has been upgraded to support **real-time live notifications** via WebSocket. When a notification is sent, it now appears instantly on all member accounts without requiring a page refresh.

## Key Features

1. **Real-time WebSocket notifications** - Notifications appear instantly
2. **Staff/Member account separation** - Target notifications to specific user groups
3. **Priority levels** - Urgent, High, Normal, Low priorities with visual indicators
4. **Per-user notification tracking** - Each user has their own notification inbox
5. **Modern UI components** - Updated notification dropdown, badges, and panels

## Database Migration

Run the migration to add the new fields:

```bash
python3 manage.py migrate notifications
```

## Dependencies

Install the new dependencies (already added to requirements.txt):

```bash
pip install channels channels-redis daphne
```

## Configuration

### 1. Environment Variables (optional)

Add these to your `.env` file for Redis configuration:

```
# Redis for WebSocket support (optional - defaults to local memory)
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
USE_INMEMORY_CHANNEL_LAYER=True  # Use True for development
```

### 2. Running with WebSocket Support

For development (using in-memory channel layer):
```bash
python3 manage.py runserver
```

For production with Redis:
```bash
# Start Redis server
redis-server

# Run with Daphne (ASGI server)
daphne -b 0.0.0.0 -p 8000 christ_king_church.asgi:application
```

## New Fields Added

### Notification Model
- `target_audience`: Who receives the notification (All, Staff Only, Members Only, Portal Only)
- `priority`: Priority level (low, normal, high, urgent)

### New UserNotification Model
- Tracks individual notifications per user
- Tracks read/unread status
- Tracks WebSocket delivery status

## URL Routes

- `/notifications/my/` - User's notification inbox
- `/notifications/my/<id>/` - View specific notification
- `/notifications/api/my/` - API for user's notifications
- `ws/notifications/` - WebSocket endpoint for real-time updates

## Usage

### Creating a Notification

When creating a notification, you can now:
1. Set **Priority** (Urgent, High, Normal, Low)
2. Set **Target Audience**:
   - All Users - Both staff and members see it
   - Staff Only - Only staff/admin accounts
   - Members Only - Only regular members
   - Portal Members Only - Only active portal users

### In Templates

Include the notification dropdown in your navbar:

```html
{% include 'notifications/_notification_dropdown.html' %}
```

Include the WebSocket JavaScript in your base template:

```html
<script src="{% static 'notifications/js/notification_websocket.js' %}"></script>
```

## How It Works

1. When a notification is created and sent:
   - `create_user_notifications()` creates UserNotification records for each target user
   - `broadcast_notification()` sends WebSocket messages to connected clients

2. Connected clients receive the notification instantly via WebSocket

3. If WebSocket is unavailable, the system falls back to HTTP polling every 30 seconds

## Target Audience Logic

- **All Users**: Sends to both `staff_notifications` and `member_notifications` groups
- **Staff Only**: Sends only to `staff_notifications` group (is_staff=True)
- **Members Only**: Sends only to `member_notifications` group (is_staff=False)
- **Portal Members Only**: Sends to individual user notification groups

## Files Modified/Created

### Models
- `notifications/models.py` - Added target_audience, priority, UserNotification model

### Views
- `notifications/views.py` - Added user notification views (my_notifications, user_notification_detail, etc.)

### Templates
- `notifications/_notification_dropdown.html` - New modern dropdown component
- `notifications/my_notifications.html` - User's notification inbox
- `notifications/user_notification_detail.html` - Notification detail view
- `notifications/notification_form.html` - Updated with new fields
- `notifications/notification_list.html` - Modernized with stats cards
- `notifications/notification_detail.html` - Modernized with priority indicators

### JavaScript
- `static/notifications/js/notification_websocket.js` - WebSocket client

### Configuration
- `requirements.txt` - Added channels, channels-redis, daphne
- `christ_king_church/settings.py` - Added Channels configuration
- `christ_king_church/asgi.py` - Updated for WebSocket support
- `notifications/routing.py` - WebSocket routing
- `notifications/consumers.py` - WebSocket consumer
- `notifications/utils.py` - Added broadcast_notification function
- `notifications/migrations/0004_add_live_notification_system.py` - Migration

## Testing

1. Create a notification with target_audience = "All Users"
2. Open the portal in two different browsers/sessions
3. Send the notification
4. Both sessions should receive the notification instantly without refresh

## Troubleshooting

### WebSocket not connecting
- Check browser console for errors
- Ensure `USE_INMEMORY_CHANNEL_LAYER=True` in development
- For production, ensure Redis is running

### Notifications not appearing
- Check that the WebSocket JavaScript is included
- Verify the notification dropdown template is included in your navbar
- Check that user is authenticated (WebSocket only connects for logged-in users)

## Future Enhancements

- Email notifications for high/urgent priority
- Push notifications for mobile app
- Scheduled notifications
- Notification templates
- Advanced filtering and search
