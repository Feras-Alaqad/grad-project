"""
DEPRECATED: This module is kept for backward compatibility only.
Please use api.services.email_service.EmailService for new code.

This file provides legacy email rendering functions that are now replaced
by Django templates in templates/emails/ and the EmailService class.

Migration Guide:
    Old:
        from api.email_utils import render_welcome_email
        html = render_welcome_email(user.name, user.email, request)
        
    New:
        from api.services.email_service import EmailService
        service = EmailService(request)
        service.send_welcome_email(user)
"""

from django.conf import settings
from django.utils.translation import gettext as _
from django.template.loader import render_to_string
import warnings

# Legacy color constants (deprecated)
PRIMARY_COLOR = "#3CB54B"  
PRIMARY_DARK = "#0b1220"   
BG_COLOR = "#f3f4f6"       
TEXT_PRIMARY = "#0f172a"   
TEXT_SECONDARY = "#374151"


def absolute_media_url(path: str, request=None) -> str:
    """
    DEPRECATED: Use EmailService._get_logo_url() instead.
    Get absolute URL for a media file.
    """
    media_url = getattr(settings, 'MEDIA_URL', '/media/')
    if not media_url.startswith('/'):
        media_url = '/' + media_url
    media_path = f"{media_url}{path}".replace('//', '/')
    if request:
        return request.build_absolute_uri(media_path)
    base = getattr(settings, 'BASE_URL', 'http://localhost:8000')
    if base.endswith('/'):
        base = base[:-1]
    return f"{base}{media_path}"


def logo_header_html(request=None, image_url: str | None = None) -> str:
    """DEPRECATED: Use Django templates instead."""
    warnings.warn(
        "logo_header_html is deprecated. Use Django email templates instead.",
        DeprecationWarning,
        stacklevel=2
    )
    logo_src = image_url or absolute_media_url('awnlogo.png', request)
    return (
        f"<tr>"
        f"  <td align=\"center\" style=\"padding:20px 0;\">"
        f"    <img src=\"{logo_src}\" alt=\"AWN Platform Logo\" style=\"height:56px;display:block;\"/>"
        f"  </td>"
        f"</tr>"
    )


def banner_header_html(request=None, image_url: str | None = None) -> str:
    """DEPRECATED: Use Django templates instead."""
    warnings.warn(
        "banner_header_html is deprecated. Use Django email templates instead.",
        DeprecationWarning,
        stacklevel=2
    )
    logo_src = image_url or absolute_media_url('awnlogo.png', request)
    return (
        f"<tr>"
        f"  <td style=\"background:#5b6cfb;border-top-left-radius:16px;border-top-right-radius:16px;\">"
        f"    <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\">"
        f"      <tr>"
        f"        <td align=\"left\" style=\"padding:22px 24px;\">"
        f"          <img src=\"{logo_src}\" alt=\"Logo\" style=\"height:40px;display:block;\"/>"
        f"        </td>"
        f"      </tr>"
        f"    </table>"
        f"  </td>"
        f"</tr>"
    )


def render_notification_email(
    title: str, 
    message: str, 
    request=None, 
    cta_url: str | None = None, 
    cta_label: str | None = None, 
    reply_html: str | None = None, 
    signoff_text: str | None = None
) -> str:
    """
    DEPRECATED: Use EmailService.send_notification_email() instead.
    
    Render a notification email using Django templates.
    This function now uses the new template system for backward compatibility.
    """
    logo_url = absolute_media_url('awnlogo.png', request)
    
    context = {
        'logo_url': logo_url,
        'title': title,
        'message': message,
        'cta_url': cta_url,
        'cta_label': cta_label or _('Get Started'),
        'reply_html': reply_html,
        'signoff_text': signoff_text or _('AWN Platform'),
        'platform_url': getattr(settings, 'PLATFORM_URL', 'https://awn-three.vercel.app'),
    }
    
    return render_to_string('emails/notification.html', context, request=request)



def render_welcome_email(user_name: str, user_email: str, request=None, is_organization: bool = False) -> str:
    """
    DEPRECATED: Use EmailService.send_welcome_email() instead.
    
    Render welcome email for new registered users.
    """
    logo_url = absolute_media_url('awnlogo.png', request)
    platform_url = getattr(settings, 'PLATFORM_URL', 'https://awn-three.vercel.app')
    
    context = {
        'logo_url': logo_url,
        'user_name': user_name,
        'user_email': user_email,
        'is_organization': is_organization,
        'cta_url': f"{platform_url}/login",
        'cta_label': _("Get Started"),
        'platform_url': platform_url,
    }
    
    return render_to_string('emails/welcome.html', context, request=request)


def render_admin_support_notification_email(support_request, request=None) -> str:
    """
    DEPRECATED: Use EmailService.send_admin_support_notification() instead.
    
    Render admin notification email for new support requests.
    """
    logo_url = absolute_media_url('awnlogo.png', request)
    platform_url = getattr(settings, 'PLATFORM_URL', 'https://awn-three.vercel.app')
    
    context = {
        'logo_url': logo_url,
        'request_title': support_request.title,
        'request_type': support_request.get_type_display(),
        'request_id': support_request.id,
        'request_description': support_request.description,
        'user_name': support_request.user.name or 'N/A',
        'user_email': support_request.user.email,
        'cta_url': f"{platform_url}/admin/support",
        'platform_url': platform_url,
    }
    
    return render_to_string('emails/admin_support_notification.html', context, request=request)