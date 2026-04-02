from django.urls import path
from . import views

urlpatterns = [
    path('', views.analytics_dashboard, name='analytics_dashboard'),
    path('api/tithes/', views.tithe_analytics_api, name='tithe_analytics_api'),
    path('api/finance/', views.finance_analytics_api, name='finance_analytics_api'),
    path('api/members/', views.member_analytics_api, name='member_analytics_api'),
    path('reports/tithes/', views.tithing_report, name='tithing_report'),
    path('reports/finance/', views.financial_report, name='financial_report'),
]
