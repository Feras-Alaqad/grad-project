from django.conf import settings
from django.utils.translation import gettext as _

# Brand palette aligned with AWN logo and theme
PRIMARY_COLOR = "#009091"  # primary brand color
PRIMARY_DARK = "#0b1220"   # darker footer/background for improved dark mode
BG_COLOR = "#f3f4f6"       # page background
TEXT_PRIMARY = "#0f172a"   # main text color (slate-900)
TEXT_SECONDARY = "#374151" # secondary text color with better contrast

def absolute_media_url(path: str, request=None) -> str:
    """Build an absolute URL for a media file using request or BASE_URL.

    - If `request` is provided, use `request.build_absolute_uri(media_path)` to match
      how profile image URLs are generated for reliability behind proxies.
    - Otherwise, fall back to `BASE_URL + MEDIA_URL`.
    """
    media_url = getattr(settings, 'MEDIA_URL', '/media/')
    # Normalize media URL prefix
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
    """Return a table row containing the AWN logo for email headers.

    Accepts optional `request` to build absolute URL like profile pictures,
    and optional `image_url` to override the logo source if provided.
    """
    logo_src = image_url or absolute_media_url('awnlogo.png', request)
    return (
        f"<tr>"
        f"  <td align=\"center\" style=\"padding:20px 0;\">"
        f"    <img src=\"{logo_src}\" alt=\"AWN Platform Logo\" style=\"height:56px;display:block;\"/>"
        f"  </td>"
        f"</tr>"
    )


def banner_header_html(request=None, image_url: str | None = None) -> str:
    """Return a full-width banner row with purple background and rounded corners.

    - Centers the logo image at the top, matching the provided design.
    - Uses `request` to build absolute logo URL when available.
    - Allows overriding the logo with `image_url`.
    """
    logo_src = image_url or absolute_media_url('awnlogo.png', request)
    # Top banner with rounded top corners and purple background
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


def render_notification_email(title: str, message: str, request=None, cta_url: str | None = None, cta_label: str | None = None) -> str:
    """Professional, brand-colored notification email with optional CTA.

    Layout:
    - White header with logo (rounded corners)
    - Centered hero icon, clear title, friendly copy
    - Optional primary action button with AWN Platform branding
    - Dark brand footer with contact link
    """
    logo_src = absolute_media_url('awnlogo.png', request)
    cta_block = (
        f"<table role=\"presentation\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\"><tr><td style=\"border-radius:8px;\">"
        f"<a href=\"{cta_url}\" style=\"background:{PRIMARY_COLOR};color:#ffffff;text-decoration:none;padding:12px 18px;display:inline-block;border-radius:8px;font-weight:600;\">"
        f"{cta_label if cta_label else _('Get Started')}"
        f"</a></td></tr></table>"
        if cta_url
        else ""
    )

    # Build a white header with logo only (left aligned)
    header_html = (
        f"<tr><td class=\"awn-header\" style=\"background:#ffffff;border-top-left-radius:16px;border-top-right-radius:16px;\">"
        f"<table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\">"
        f"<tr>"
        f"  <td align=\"left\" style=\"padding:16px 24px;\">"
        f"    <img src=\"{logo_src}\" alt=\"AWN Platform Logo\" style=\"height:28px;display:block;\"/>"
        f"  </td>"
        f"</tr>"
        f"</table>"
        f"</td></tr>"
    )

    # Brand footer with Contact Us email link and website link
    footer_html = (
        f"<tr><td class=\"awn-footer\" style=\"background:{PRIMARY_DARK};color:#e5e7eb;border-bottom-left-radius:16px;border-bottom-right-radius:16px;\">"
        f"<table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\">"
        f"<tr><td align=\"center\" style=\"padding:20px 24px;text-align:center;\">"
        f"<table class=\"footer-inline\" role=\"presentation\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" style=\"display:inline-table;\">"
        f"<tr><td style=\"vertical-align:middle;padding-right:8px;\"><img src=\"{logo_src}\" alt=\"AWN Platform\" style=\"height:28px;display:block;\"/></td>"
        f"<td style=\"vertical-align:middle;color:#e5e7eb;font-size:16px;font-weight:600;font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display','SF Pro Text',Helvetica,Arial,sans-serif;\">AWN Platform</td></tr>"
        f"</table>"
        f"</td></tr>"
        f"<tr><td class=\"footer-links\" align=\"center\" style=\"padding:8px 24px;font-size:14px;text-align:center;\"><a href=\"mailto:awnpaltform@gmail.com\" style=\"color:#cbd5e1;text-decoration:none;\">{_('Contact Us')}</a> • <a href=\"https://awn-three.vercel.app\" style=\"color:#cbd5e1;text-decoration:none;\">{_('Visit Website')}</a></td></tr>"
        f"</table>"
        f"</td></tr>"
    )

    return (
        f"""
<!DOCTYPE html>
<html>
  <head>
    <meta charset=\"utf-8\">
    <title>{title}</title>
    <meta name=\"color-scheme\" content=\"light dark\">
    <meta name=\"supported-color-schemes\" content=\"light dark\">
    <style>
      @media (prefers-color-scheme: dark) {{
        body {{ background-color: {PRIMARY_DARK} !important; }}
        .awn-card {{ background: #1a202c !important; border-color: #2d3748 !important; }}
        .awn-header {{ background: #1a202c !important; }}
        .awn-title {{ color: #f7fafc !important; }}
        .awn-text {{ color: #e2e8f0 !important; }}
        .awn-footer {{ background: {PRIMARY_DARK} !important; }}
        .awn-btn {{ background: #7c8cfb !important; color: #ffffff !important; }}
        .awn-brand {{ color: #f7fafc !important; }}
      }}
      @media only screen and (max-width: 480px) {{
        .footer-inline {{ display: block !important; }}
        .footer-links {{ text-align: left !important; }}
        .awn-footer td {{ text-align: left !important; }}
      }}
    </style>
  </head>
  <body style=\"margin:0;padding:0;background-color:{BG_COLOR};\">
    <table role=\"presentation\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" width=\"100%\"> 
      <tr>
        <td align=\"center\" style=\"padding:24px;\">
          <table class=\"awn-card\" role=\"presentation\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" width=\"600\" style=\"background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display','SF Pro Text',Helvetica,Arial,sans-serif;\">
            {header_html}
            <tr>
              <td style=\"padding:28px 24px 24px;\" align=\"center\">
                <h1 class=\"awn-title\" style=\"margin:0 0 10px;font-size:28px;color:{TEXT_PRIMARY};font-weight:700;letter-spacing:-0.5px;\">{title}</h1>
                <p class=\"awn-text\" style=\"margin:0 0 20px;color:{TEXT_SECONDARY};font-size:16px;line-height:1.6;\">{message}</p>
                {cta_block}
                <p class=\"awn-brand\" style=\"margin:18px 0 0;color:#64748b;font-size:14px;font-weight:500;\">{_('Regards')},<br/>AWN Platform</p>
              </td>
            </tr>
            {footer_html}
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
""".strip()
    )


def render_welcome_email(user_name: str, user_email: str, request=None) -> str:
    """Welcome email for new registered users with AWN Platform branding."""
    title = _("Welcome to AWN Platform!")
    message = _(
        "Thank you for joining AWN Platform! We're excited to have you as part of our community. "
        "You can now explore announcements, connect with organizations, and track your applications all in one place."
    )
    cta_url = "https://awn-three.vercel.app/login"
    cta_label = _("Get Started")
    
    return render_notification_email(
        title=title,
        message=message,
        request=request,
        cta_url=cta_url,
        cta_label=cta_label
    )


def render_admin_support_notification_email(support_request, request=None) -> str:
    """Admin notification email for new support requests."""
    title = _("New Support Request Received")
    message = _(
        f"A new support request has been submitted by {support_request.user.name or support_request.user.email}.\n\n"
        f"Request Details:\n"
        f"• Title: {support_request.title}\n"
        f"• Type: {support_request.get_type_display()}\n"
        f"• User: {support_request.user.name} ({support_request.user.email})\n"
        f"• Request ID: #{support_request.id}\n\n"
        f"Description:\n{support_request.description}\n\n"
        "Please review and respond to this request in the admin panel."
    )
    cta_url = f"https://awn-three.vercel.app/"
    cta_label = _("View Request")
    
    return render_notification_email(
        title=title,
        message=message,
        request=request,
        cta_url=cta_url,
        cta_label=cta_label
    )