from django.conf import settings

def absolute_media_url(path: str) -> str:
    """Build an absolute URL for a media file using BASE_URL and MEDIA_URL."""
    base = getattr(settings, 'BASE_URL', 'http://localhost:8000')
    media_url = getattr(settings, 'MEDIA_URL', '/media/')
    # Ensure slashes handled correctly
    if not base.endswith('/'):
        base += ''
    if not media_url.startswith('/'):
        media_url = '/' + media_url
    return f"{base}{media_url}{path}".replace('//media', '/media')


def logo_header_html() -> str:
    """Return a table row containing the AWN logo for email headers."""
    logo_src = absolute_media_url('awnlogo.png')
    return (
        f"<tr>"
        f"  <td align=\"center\" style=\"padding:16px 0;\">"
        f"    <img src=\"{logo_src}\" alt=\"AWN\" style=\"height:40px;display:block;\"/>"
        f"  </td>"
        f"</tr>"
    )