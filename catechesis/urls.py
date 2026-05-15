from django.urls import path
from . import views
from users.views import pending_sacraments_list, verify_sacrament, sacrament_detail

urlpatterns = [
    path('', views.member_list, name='member_list'),
    path('register/', views.member_register, name='member_register'),
    path('member/<int:pk>/', views.member_detail, name='member_detail'),
    path('member/<int:pk>/delete/', views.member_delete, name='member_delete'),
    path('member/<int:member_pk>/request-sacrament/', views.sacrament_request_create, name='sacrament_request'),
    path('sacraments/', views.sacrament_list, name='sacrament_list'),
    
    # Sacrament Request Management
    path('request/<int:pk>/delete/', views.sacrament_request_delete, name='sacrament_request_delete'),
    
    # Approval workflow for CatechesisMember
    path('pending-requests/', views.pending_requests, name='pending_requests'),
    path('review/<int:pk>/', views.review_request, name='review_request'),
    path('complete/<int:pk>/', views.complete_request, name='complete_request'),
    
    # Calendar & Analytics
    path('calendar/', views.sacrament_calendar, name='sacrament_calendar'),
    path('calendar/<int:year>/<int:month>/', views.sacrament_calendar, name='sacrament_calendar_month'),
    path('analytics/', views.analytics_dashboard, name='catechesis_analytics'),
    path('member/<int:pk>/analytics/', views.member_analytics, name='member_analytics'),
    
    # MemberSacrament Verification (from users app)
    path('verification/', pending_sacraments_list, name='pending_sacraments_list'),
    path('verification/<int:sacrament_id>/', sacrament_detail, name='sacrament_detail'),
    path('verification/<int:sacrament_id>/review/', verify_sacrament, name='verify_sacrament'),
    
    # Sacrament Classes & Attendance
    path('classes/', views.sacrament_class_list, name='class_list'),
    path('classes/<int:pk>/attendance/', views.take_attendance, name='take_attendance'),
    path('classes/<int:pk>/attendance/view/', views.view_attendance, name='view_attendance'),
    
    # Export
    path('export/', views.export_students, name='export_students'),
]