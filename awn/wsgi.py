"""
WSGI config for awn project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys
from pathlib import Path

from django.core.wsgi import get_wsgi_application

# Add the project directory to the Python path
project_dir = Path(__file__).resolve().parent.parent
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))

# Set the settings module based on environment
# Use production settings if DJANGO_ENV is set to 'production'
if os.environ.get('DJANGO_ENV') == 'production':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'awn.settings_production')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'awn.settings')

# Initialize Django application
application = get_wsgi_application()

# Optional: Add middleware for better production handling
try:
    from whitenoise import WhiteNoise
    # Serve static files with WhiteNoise if available
    application = WhiteNoise(application)
    # Add static files directory
    static_root = os.path.join(project_dir, 'staticfiles')
    if os.path.exists(static_root):
        application.add_files(static_root, prefix='/static/')
    
    # Add media files directory
    media_root = os.path.join(project_dir, 'media')
    if os.path.exists(media_root):
        application.add_files(media_root, prefix='/media/')
except ImportError:
    # WhiteNoise not available, continue without it
    pass
