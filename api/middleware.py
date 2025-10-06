from django.utils import translation
from django.conf import settings
from django.utils.translation import get_language_from_request


class LanguageMiddleware:
    """
    Enhanced middleware to work with Django's i18n_patterns and provide
    additional language detection features.
    Supports /ar/ for Arabic and /en/ for English routes.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Let Django's LocaleMiddleware handle the basic language detection first
        # Then enhance it with our custom logic
        language = self.get_language_from_request(request)
        
        # Only override if we have a specific preference
        if language:
            translation.activate(language)
            request.LANGUAGE_CODE = language
        
        # Process the request
        response = self.get_response(request)
        
        # Add language information to response headers for frontend
        if hasattr(request, 'LANGUAGE_CODE'):
            response['Content-Language'] = request.LANGUAGE_CODE
        
        return response

    def get_language_from_request(self, request):
        """
        Enhanced language detection that works with Django's i18n_patterns.
        Priority order:
        1. User profile preference (if authenticated)
        2. Session language preference
        3. Let Django's LocaleMiddleware handle URL and Accept-Language
        """
        # Check user profile if authenticated
        if hasattr(request, 'user') and request.user.is_authenticated:
            if hasattr(request.user, 'preferred_language'):
                user_lang = getattr(request.user, 'preferred_language', None)
                if user_lang in ['ar', 'en']:
                    return user_lang
        
        # Check session for language preference
        session_lang = request.session.get('django_language')
        if session_lang in ['ar', 'en']:
            return session_lang
        
        # Let Django's LocaleMiddleware handle the rest
        # (URL patterns, Accept-Language header, etc.)
        return None

    def get_language_from_path(self, path):
        """Extract language code from URL path"""
        if path.startswith('/ar/'):
            return 'ar'
        elif path.startswith('/en/'):
            return 'en'
        return None