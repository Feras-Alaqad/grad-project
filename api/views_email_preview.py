"""
Email Preview View (Development Only)

Add this to your urls.py for development:
    path('dev/email-preview/', email_preview, name='email_preview'),

Then visit: http://localhost:8000/dev/email-preview/
"""

from django.http import HttpResponse
from django.shortcuts import render
from api.services.email_service import EmailService


def email_preview(request):
    """
    Preview email templates in browser (development only).
    
    Usage:
        /dev/email-preview/                    # List all templates
        /dev/email-preview/?template=welcome   # Preview specific template
    """
    
    # Get template name from query params
    template_name = request.GET.get('template', '')
    
    # Available templates with mock data
    templates = {
        'welcome': {
            'name': 'Welcome Email',
            'context': {
                'user_name': 'John Doe',
                'user_email': 'john@example.com',
                'is_organization': False,
                'cta_url': 'https://awn-three.vercel.app/login',
                'cta_label': 'Get Started',
            }
        },
        'welcome_org': {
            'name': 'Welcome Email (Organization)',
            'template': 'welcome',
            'context': {
                'user_name': 'Acme Corporation',
                'user_email': 'contact@acme.com',
                'is_organization': True,
                'cta_url': 'https://awn-three.vercel.app/login',
                'cta_label': 'Get Started',
            }
        },
        'password_reset': {
            'name': 'Password Reset',
            'context': {
                'user_name': 'John Doe',
                'user_email': 'john@example.com',
                'reset_url': 'https://awn-three.vercel.app/reset-password/token123abc',
            }
        },
        'support_received': {
            'name': 'Support Request Received',
            'context': {
                'user_name': 'John Doe',
                'user_email': 'john@example.com',
                'request_title': 'Login Issue',
                'request_id': 12345,
                'request_type': 'Technical Support',
                'cta_url': 'https://awn-three.vercel.app/support/requests',
            }
        },
        'support_reply': {
            'name': 'Support Reply',
            'context': {
                'user_name': 'John Doe',
                'user_email': 'john@example.com',
                'request_title': 'Login Issue',
                'request_id': 12345,
                'reply_text': 'Thank you for contacting us. We have investigated your login issue and found that it was caused by browser cache. Please clear your cache and try again.\n\nIf the issue persists, please let us know.',
                'cta_url': 'https://awn-three.vercel.app/support/requests',
            }
        },
        'admin_support_notification': {
            'name': 'Admin Support Notification',
            'context': {
                'request_title': 'Critical Bug Report',
                'request_type': 'Bug Report',
                'request_id': 12345,
                'request_description': 'Users are experiencing issues with the announcement feature. When trying to create a new announcement, the form validation fails even with correct data. This is affecting multiple organizations.',
                'user_name': 'John Doe',
                'user_email': 'john@example.com',
                'cta_url': 'https://awn-three.vercel.app/admin/support',
            }
        },
        'notification': {
            'name': 'Generic Notification',
            'context': {
                'title': 'Platform Update',
                'message': 'We have released a new version of AWN Platform with exciting features!\n\nNew features include:\n• Enhanced announcement management\n• Improved user dashboard\n• Better performance\n\nCheck out the updates now!',
                'cta_url': 'https://awn-three.vercel.app/updates',
                'cta_label': 'View Updates',
                'signoff_text': 'AWN Platform Team',
            }
        },
        'notification_with_reply': {
            'name': 'Notification with Reply Box',
            'template': 'notification',
            'context': {
                'title': 'Application Status Update',
                'message': 'Your application has been reviewed by our team.',
                'reply_html': 'We are pleased to inform you that your application has been approved! You can now access all platform features.\n\nNext steps:\n1. Complete your profile\n2. Explore available announcements\n3. Connect with organizations',
                'cta_url': 'https://awn-three.vercel.app/dashboard',
                'cta_label': 'Go to Dashboard',
                'signoff_text': 'AWN Platform Admin Team',
            }
        },
    }
    
    if not template_name:
        # Show template list
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Email Template Preview</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                    max-width: 800px;
                    margin: 40px auto;
                    padding: 20px;
                    background: #f3f4f6;
                }
                h1 {
                    color: #0f172a;
                    margin-bottom: 30px;
                }
                .template-list {
                    background: white;
                    border-radius: 12px;
                    padding: 20px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }
                .template-item {
                    padding: 15px;
                    border-bottom: 1px solid #e5e7eb;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                .template-item:last-child {
                    border-bottom: none;
                }
                .template-name {
                    font-weight: 600;
                    color: #0f172a;
                }
                .preview-btn {
                    background: #3CB54B;
                    color: white;
                    padding: 8px 16px;
                    border-radius: 6px;
                    text-decoration: none;
                    font-size: 14px;
                }
                .preview-btn:hover {
                    background: #2ea03d;
                }
                .warning {
                    background: #fef3c7;
                    border: 1px solid #fcd34d;
                    border-radius: 8px;
                    padding: 12px 16px;
                    margin-bottom: 20px;
                    color: #78350f;
                }
            </style>
        </head>
        <body>
            <h1>📧 Email Template Preview</h1>
            <div class="warning">
                ⚠️ This preview is for development only. Remove this view in production.
            </div>
            <div class="template-list">
        """
        
        for key, data in templates.items():
            html += f"""
                <div class="template-item">
                    <span class="template-name">{data['name']}</span>
                    <a href="?template={key}" class="preview-btn">Preview</a>
                </div>
            """
        
        html += """
            </div>
        </body>
        </html>
        """
        
        return HttpResponse(html)
    
    # Preview specific template
    if template_name not in templates:
        return HttpResponse(
            f"<h1>Template '{template_name}' not found</h1>"
            f"<a href='?'>← Back to list</a>",
            status=404
        )
    
    template_data = templates[template_name]
    template_file = template_data.get('template', template_name)
    context = template_data['context']
    
    # Render template
    service = EmailService(request)
    html_content, _ = service._render_email_template(template_file, context)
    
    # Add preview controls
    preview_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Preview: {template_data['name']}</title>
        <style>
            body {{ margin: 0; padding: 0; font-family: sans-serif; }}
            .preview-header {{
                background: #0f172a;
                color: white;
                padding: 15px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                position: sticky;
                top: 0;
                z-index: 1000;
            }}
            .back-btn {{
                background: #3CB54B;
                color: white;
                padding: 8px 16px;
                border-radius: 6px;
                text-decoration: none;
                font-size: 14px;
            }}
            .preview-content {{
                padding: 20px;
                background: #f3f4f6;
            }}
        </style>
    </head>
    <body>
        <div class="preview-header">
            <h2 style="margin: 0;">Preview: {template_data['name']}</h2>
            <a href="?" class="back-btn">← Back to List</a>
        </div>
        <div class="preview-content">
            {html_content}
        </div>
    </body>
    </html>
    """
    
    return HttpResponse(preview_html)
