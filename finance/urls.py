from django.urls import path
from . import views


urlpatterns = [
    path('financial_dashboard/', views.dashboard, name='financial_dashboard'),
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/add/', views.add_transaction, name='add_transaction'),
    path('transactions/<int:pk>/edit/', views.edit_transaction, name='edit_transaction'),
    path('transactions/<int:pk>/delete/', views.delete_transaction, name='delete_transaction'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.add_category, name='add_categories'),
    path('categories/<int:pk>/delete/', views.delete_category, name='delete_category'),
]