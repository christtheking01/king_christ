from django.urls import path
from . import views


urlpatterns = [
    # Calendar views
    path('calendar/', views.calendar_view, name='calendar'),
    path('calendar/api/', views.calendar_api, name='calendar_api'),
    
    # Liturgical calendar
    path('liturgical/', views.liturgical_calendar, name='liturgical_calendar'),
    
    # Event views
    path('', views.event_list, name='event_list'),
    path('create/', views.event_create, name='event_create'),
    path('<int:pk>/', views.event_detail, name='event_detail'),
    path('<int:pk>/edit/', views.event_edit, name='event_edit'),
    path('<int:pk>/delete/', views.event_delete, name='event_delete'),
    
    # Registration
    path('<int:pk>/register/', views.event_register, name='event_register'),
    path('registration/<int:pk>/cancel/', views.registration_cancel, name='registration_cancel'),
    path('my-registrations/', views.my_registrations, name='my_registrations'),
    
    # Dashboard
    path('dashboard/', views.events_dashboard, name='events_dashboard'),
]
