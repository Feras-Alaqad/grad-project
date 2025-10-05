from django.conf import settings

# Brand palette aligned with AWN logo and theme
PRIMARY_COLOR = "#5b6cfb"  # primary brand color
PRIMARY_DARK = "#0f172a"   # dark footer background
BG_COLOR = "#f3f4f6"       # page background
TEXT_PRIMARY = "#111827"   # main text color
TEXT_SECONDARY = "#4b5563" # secondary text color

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
    - Optional primary action button
    - Dark brand footer with helpful links
    """
    # Inline SVG hero icon uses brand color to avoid external assets
    hero_svg = (
        f"<svg width=\"40\" height=\"40\" viewBox=\"0 0 24 24\" fill=\"none\" xmlns=\"http://www.w3.org/2000/svg\" style=\"display:block;\">"
        f"  <circle cx=\"12\" cy=\"12\" r=\"10\" fill=\"{PRIMARY_COLOR}\" opacity=\"0.12\"/>"
        f"  <path d=\"M12 12c2.209 0 4-1.791 4-4s-1.791-4-4-4-4 1.791-4 4 1.791 4 4 4zm0 2c-3.314 0-6 2.239-6 5v1h12v-1c0-2.761-2.686-5-6-5z\" fill=\"{PRIMARY_COLOR}\"/>"
        f"</svg>"
    )

    cta_block = (
        f"<table role=\"presentation\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\"><tr><td style=\"border-radius:8px;\"><a href=\"{cta_url}\" style=\"background:{PRIMARY_COLOR};color:#ffffff;text-decoration:none;padding:12px 18px;display:inline-block;border-radius:8px;font-weight:600;\">{cta_label}</a></td></tr></table>"
        if cta_url and cta_label
        else ""
    )

    # Build a white header with logo (left aligned)
    logo_src = absolute_media_url('awnlogo.png', request)
    header_html = (
        f"<tr><td style=\"background:#ffffff;border-top-left-radius:16px;border-top-right-radius:16px;\">"
        f"<table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\"><tr>"
        f"<td align=\"left\" style=\"padding:16px 24px;\"><img src=\"{logo_src}\" alt=\"AWN Platform\" style=\"height:28px;display:block;\"/></td>"
        f"</tr></table>"
        f"</td></tr>"
    )

    # Brand footer
    footer_html = (
        f"<tr><td style=\"background:{PRIMARY_DARK};color:#e5e7eb;border-bottom-left-radius:16px;border-bottom-right-radius:16px;\">"
        f"<table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\">"
        f"<tr><td align=\"center\" style=\"padding:20px 24px;\"><img src=\"{logo_src}\" alt=\"AWN Platform\" style=\"height:28px;display:block;\"/></td></tr>"
        f"<tr><td align=\"center\" style=\"padding:8px 24px;font-size:14px;\"><span style=\"color:#cbd5e1;\">Privacy Policy • Contact Us • Unsubscribe</span></td></tr>"
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
  </head>
  <body style=\"margin:0;padding:0;background-color:{BG_COLOR};\">
    <table role=\"presentation\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" width=\"100%\"> 
      <tr>
        <td align=\"center\" style=\"padding:24px;\">
          <table role=\"presentation\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" width=\"600\" style=\"background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;font-family:Arial,Helvetica,sans-serif;\">
            {header_html}
            <tr>
              <td style=\"padding:24px;\" align=\"center\">
                <div style=\"width:64px;height:64px;border-radius:50%;background:#eef2ff;border:1px solid #dbeafe;display:flex;align-items:center;justify-content:center;margin:4px auto 12px;\">{hero_svg}</div>
                <h1 style=\"margin:0 0 8px;font-size:26px;color:{TEXT_PRIMARY};font-weight:800;\">{title}</h1>
                <p style=\"margin:0 0 18px;color:{TEXT_SECONDARY};font-size:16px;line-height:1.7;\">{message}</p>
                {cta_block}
                <p style=\"margin:16px 0 0;color:#6b7280;font-size:14px;\">Regards,<br/>AWN Platform</p>
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