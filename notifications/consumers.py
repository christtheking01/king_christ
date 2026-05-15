import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser


class NotificationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time notifications"""
    
    async def connect(self):
        self.user = self.scope["user"]
        
        # Reject connection if user is not authenticated
        if isinstance(self.user, AnonymousUser):
            await self.close()
            return
        
        # Create a personal notification group for this user
        self.notification_group_name = f"user_{self.user.id}_notifications"
        
        # Create staff group if user is staff
        self.is_staff = await self.check_is_staff()
        
        # Join user's personal notification group
        await self.channel_layer.group_add(
            self.notification_group_name,
            self.channel_name
        )
        
        # Join staff group if user is staff
        if self.is_staff:
            await self.channel_layer.group_add(
                "staff_notifications",
                self.channel_name
            )
        
        # Join members group
        await self.channel_layer.group_add(
            "member_notifications",
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial unread count
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'initial_count',
            'unread_count': unread_count
        }))
    
    async def disconnect(self, close_code):
        # Leave all groups
        if hasattr(self, 'notification_group_name'):
            await self.channel_layer.group_discard(
                self.notification_group_name,
                self.channel_name
            )
            
            if self.is_staff:
                await self.channel_layer.group_discard(
                    "staff_notifications",
                    self.channel_name
                )
            
            await self.channel_layer.group_discard(
                "member_notifications",
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages from client"""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'mark_read':
                notification_id = data.get('notification_id')
                await self.mark_notification_read(notification_id)
                unread_count = await self.get_unread_count()
                await self.send(text_data=json.dumps({
                    'type': 'unread_count_updated',
                    'unread_count': unread_count
                }))
            
            elif action == 'mark_all_read':
                await self.mark_all_notifications_read()
                await self.send(text_data=json.dumps({
                    'type': 'unread_count_updated',
                    'unread_count': 0
                }))
                
            elif action == 'fetch_unread':
                notifications = await self.get_unread_notifications()
                await self.send(text_data=json.dumps({
                    'type': 'unread_notifications',
                    'notifications': notifications
                }))
                
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
    
    async def notification_message(self, event):
        """Handle notification messages sent to this consumer's group"""
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'notification': event['notification'],
            'unread_count': event.get('unread_count', 0)
        }))
    
    async def unread_count_update(self, event):
        """Handle unread count updates"""
        await self.send(text_data=json.dumps({
            'type': 'unread_count_updated',
            'unread_count': event['unread_count']
        }))
    
    @database_sync_to_async
    def check_is_staff(self):
        """Check if user is staff"""
        return self.user.is_staff or self.user.is_superuser
    
    @database_sync_to_async
    def get_unread_count(self):
        """Get unread notification count for user"""
        try:
            from .models import UserNotification
            return UserNotification.objects.filter(
                user=self.user,
                is_read=False
            ).count()
        except Exception:
            return 0
    
    @database_sync_to_async
    def get_unread_notifications(self):
        """Get unread notifications for user"""
        try:
            from .models import UserNotification
            notifications = UserNotification.objects.filter(
                user=self.user,
                is_read=False
            ).select_related('notification').order_by('-notification__created_at')[:10]
            
            return [
                {
                    'id': un.notification.id,
                    'title': un.notification.title,
                    'message': un.notification.message,
                    'created_at': un.notification.created_at.isoformat(),
                    'type': self._get_notification_type(un.notification),
                    'priority': un.notification.priority if hasattr(un.notification, 'priority') else 'normal',
                }
                for un in notifications
            ]
        except Exception as e:
            return []
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark a notification as read"""
        try:
            from .models import UserNotification
            UserNotification.objects.filter(
                user=self.user,
                notification_id=notification_id
            ).update(is_read=True)
        except Exception:
            pass
    
    @database_sync_to_async
    def mark_all_notifications_read(self):
        """Mark all notifications as read"""
        try:
            from .models import UserNotification
            UserNotification.objects.filter(
                user=self.user,
                is_read=False
            ).update(is_read=True)
        except Exception:
            pass
    
    def _get_notification_type(self, notification):
        """Determine notification type"""
        type_map = {
            'ALL': 'info',
            'MEMBER': 'info',
            'MINISTRY': 'success',
            'COMMUNITY': 'warning',
            'Staff': 'primary',
        }
        return type_map.get(notification.recipient_type, 'info')
