from django.urls import path
from . import views

urlpatterns = [
    path('', views.member_list, name='member_list'),
    path('register/', views.member_register, name='member_register'),
    path('member/<int:pk>/', views.member_detail, name='member_detail'),
    path('member/<int:member_pk>/request-sacrament/', views.sacrament_request_create, name='sacrament_request'),
    path('sacraments/', views.sacrament_list, name='sacrament_list'),
    
    # Approval workflow
    path('pending-requests/', views.pending_requests, name='pending_requests'),
    path('review/<int:pk>/', views.review_request, name='review_request'),
    path('complete/<int:pk>/', views.complete_request, name='complete_request'),
]