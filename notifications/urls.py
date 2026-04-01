from django.urls import path
from . import views


urlpatterns = [
    path('notifications/list', views.notification_list, name='notification_list'),
    path('notifications/create/', views.notification_create, name='notification_create'),
    path('notifications/<int:pk>/', views.notification_detail, name='notification_detail'),
    path('notifications/<int:pk>/send/', views.notification_send, name='notification_send'),
    path('notifications/<int:pk>/preview/', views.notification_preview, name='notification_preview'),
    path('api/unread/', views.unread_notifications_api, name='unread_notifications_api'),
    path('api/mark-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('api/mark-all-read/', views.mark_all_read, name='mark_all_read'),
]