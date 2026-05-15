from django.urls import path
from . import views


urlpatterns = [
    # Admin notification management
    path('list/', views.notification_list, name='notification_list'),
    path('create/', views.notification_create, name='notification_create'),
    path('send-to-member/', views.send_to_member, name='send_to_member'),
    path('send-to-custom/', views.send_to_custom, name='send_to_custom'),
    path('send-tithe-reminder/', views.send_tithe_reminder, name='send_tithe_reminder'),
    path('send-pledge-reminder/', views.send_pledge_reminder, name='send_pledge_reminder'),
    path('<int:pk>/', views.notification_detail, name='notification_detail'),
    path('<int:pk>/send/', views.notification_send, name='notification_send'),
    path('<int:pk>/preview/', views.notification_preview, name='notification_preview'),
    path('<int:pk>/delete/', views.notification_delete, name='notification_delete'),
    
    # Legacy API endpoints
    path('api/unread/', views.unread_notifications_api, name='unread_notifications_api'),
    path('api/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('api/mark-all-read/', views.mark_all_read, name='mark_all_read'),
    
    # User notification views (for individual users)
    path('my/', views.my_notifications, name='my_notifications'),
    path('my/<int:pk>/', views.user_notification_detail, name='user_notification_detail'),
    path('api/my/', views.user_notifications_api, name='user_notifications_api'),
    path('api/my/<int:pk>/mark-read/', views.user_notification_mark_read, name='user_notification_mark_read'),
    path('api/my/mark-all-read/', views.user_notification_mark_all_read, name='user_notification_mark_all_read'),

    # africa talking api
    path('sms/incoming/', views.sms_incoming, name='sms_incoming'),
    path('sms/delivery/', views.sms_delivery_report, name='sms_delivery_report'),
]