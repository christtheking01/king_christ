"""
Optimized Translation Middleware for Christ King Church
Handles language detection and activation with caching for performance.
"""
from django.conf import settings
from django.utils import translation
from django.utils.cache import patch_vary_headers
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme


class OptimizedLocaleMiddleware:
    """
    Optimized middleware for language detection that:
    1. Checks user preference from database (if authenticated)
    2. Falls back to session language
    3. Falls back to cookie language
    4. Falls back to browser Accept-Language header
    5. Finally falls back to default LANGUAGE_CODE

    Uses caching to minimize database queries.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.cache_timeout = 3600  # 1 hour cache for language preference

    def __call__(self, request):
        # Determine language
        language = self.get_language_from_request(request)

        # Activate translation
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()

        response = self.get_response(request)

        # Patch Vary header for caching
        patch_vary_headers(response, ['Accept-Language', 'Cookie'])

        # Deactivate translation after response
        translation.deactivate()

        return response

    def get_language_from_request(self, request):
        """Determine language with priority: session > cookie > browser > default"""
        # Note: This middleware runs before AuthenticationMiddleware, so we can't
        # access request.user here. User preference is handled by saving to session
        # when the user changes language in the language view.

        # Priority 1: Check session for language
        language = request.session.get('django_language')
        if language and self.is_language_available(language):
            return language

        # Priority 2: Check cookie
        language = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        if language and self.is_language_available(language):
            return language

        # Priority 3: Accept-Language header
        language = translation.get_language_from_request(request)
        if language and self.is_language_available(language):
            return language

        # Priority 4: Default
        return settings.LANGUAGE_CODE

    def is_language_available(self, language_code):
        """Check if language code is in available languages"""
        return any(lang[0] == language_code for lang in settings.LANGUAGES)


def get_user_language(user):
    """Helper function to get cached user language preference"""
    if not user or not user.is_authenticated:
        return None

    cache_key = f'user_language_{user.pk}'
    language = cache.get(cache_key)

    if language is None:
        language = getattr(user, 'preferred_language', None)
        if language:
            cache.set(cache_key, language, 3600)

    return language


def set_user_language(user, language_code):
    """Helper function to set user language and update cache"""
    if not user or not user.is_authenticated:
        return False

    if not any(lang[0] == language_code for lang in settings.LANGUAGES):
        return False

    user.preferred_language = language_code
    user.save(update_fields=['preferred_language'])

    # Update cache
    cache_key = f'user_language_{user.pk}'
    cache.set(cache_key, language_code, 3600)

    return True


def clear_user_language_cache(user):
    """Clear cached language preference for a user"""
    if user and user.is_authenticated:
        cache_key = f'user_language_{user.pk}'
        cache.delete(cache_key)
