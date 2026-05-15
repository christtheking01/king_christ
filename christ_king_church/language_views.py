"""
Custom language switcher view to handle language changes properly.
"""
from django.http import HttpResponseRedirect
from django.conf import settings
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import check_for_language, activate
from .translation_middleware import set_user_language, clear_user_language_cache


def set_language(request):
    """
    Optimized language switcher that:
    1. Sets language in user profile (if authenticated) - PERSISTENT
    2. Sets language in session
    3. Sets language cookie
    4. Activates translation immediately
    """
    next_url = request.POST.get('next', request.GET.get('next', '/'))

    # Security check for redirect URL
    if not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = '/'

    if request.method == 'POST':
        lang_code = request.POST.get('language')
        if lang_code and check_for_language(lang_code):
            # Priority 1: Save to user profile if authenticated (PERSISTENT)
            if request.user.is_authenticated:
                set_user_language(request.user, lang_code)

            # Priority 2: Set in session
            if hasattr(request, 'session'):
                request.session['django_language'] = lang_code
                request.session.modified = True

            # Priority 3: Activate immediately for this request
            activate(lang_code)

            # Priority 4: Set language cookie
            response = HttpResponseRedirect(next_url)
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                lang_code,
                max_age=settings.LANGUAGE_COOKIE_AGE,
                path=settings.LANGUAGE_COOKIE_PATH,
                domain=settings.LANGUAGE_COOKIE_DOMAIN,
                secure=settings.LANGUAGE_COOKIE_SECURE,
                httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
                samesite=settings.LANGUAGE_COOKIE_SAMESITE,
            )
            return response

    return HttpResponseRedirect(next_url)
