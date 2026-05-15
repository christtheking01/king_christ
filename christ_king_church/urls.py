"""
URL configuration for christ_king_church project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.utils.translation import gettext_lazy as _
from django.views.generic import RedirectView

from .views import index, permission_denied_view
from .language_views import set_language

# Custom error handlers
handler403 = permission_denied_view

# Non-i18n patterns (admin, API, etc.)
urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/setlang/', set_language, name='set_language'),
    # Favicon redirect to static file
    path('favicon.ico', RedirectView.as_view(url='/static/images/favicon.ico', permanent=True)),
]

# Main URL patterns (accessible without language prefix for default language)
main_patterns = [
    path('', index, name='index'),
    path('members/', include('member.urls')),
    path('accounts/', include('users.urls')),
    path('tithe/', include('tithe.urls')),
    path('notifications/', include('notifications.urls')),
    path('financial/', include('finance.urls')),
    path('catechesis/', include('catechesis.urls')),
    path('audit/', include('audits.urls')),
    path('analytics/', include('analytics.urls')),
    path('events/', include('events.urls')),
    path('home/', include('home.urls')),
]

# Add main patterns without language prefix (default language)
urlpatterns += main_patterns

# i18n patterns with language prefix (e.g., /sw/ for Swahili)
urlpatterns += i18n_patterns(
    *main_patterns,
    prefix_default_language=False,
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)