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