from django.urls import path
from .views import home, home_redirect

urlpatterns = [
    path('', home, name='home'),
    path('home/', home_redirect, name='home_redirect'),
]
