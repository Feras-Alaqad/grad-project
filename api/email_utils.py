from django.conf import settings

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


def render_notification_email(title: str, message: str, request=None) -> str:
    """Return HTML for notification emails mirroring the Forgot Password layout.

    - Uses the same banner header (purple) via `banner_header_html`
    - Matches card styling: background #e5e7eb, 600px container, 16px radius
    - Typography aligned with reset email for consistency
    """
    return (
        f"""
<!DOCTYPE html>
<html>
  <head>
    <meta charset=\"utf-8\">
    <title>{title}</title>
  </head>
  <body style=\"margin:0;padding:0;background-color:#e5e7eb;\">
    <table role=\"presentation\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" width=\"100%\"> 
      <tr>
        <td align=\"center\" style=\"padding:24px;\">
          <table role=\"presentation\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" width=\"600\" style=\"background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;font-family:Arial,Helvetica,sans-serif;font-size:16px;\">
            {banner_header_html(request)}
            <tr>
              <td style=\"padding:24px;\">
                <h2 style=\"margin:0 0 8px;font-size:28px;color:#111827;font-weight:800;\">{title}</h2>
                <p style=\"margin:0 0 16px;color:#4b5563;font-size:16px;line-height:1.6;\">{message}</p>
                <p style=\"margin:0;color:#6b7280;font-size:15px;\">Regards,<br/>AWN Platform</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
""".strip()
    )