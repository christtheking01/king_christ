from django.urls import path
from . import views


urlpatterns = [
    path('notifications/list', views.notification_list, name='notification_list'),
    path('notifications/create/', views.notification_create, name='notification_create'),
    path('notifications/<int:pk>/', views.notification_detail, name='notification_detail'),
    path('notifications/<int:pk>/send/', views.notification_send, name='notification_send'),
    path('notifications/<int:pk>/preview/', views.notification_preview, name='notification_preview'),
]