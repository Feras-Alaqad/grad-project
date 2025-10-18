"""
Email Service Module

This module provides a clean interface for sending emails in the AWN Platform.
It uses Django templates for better maintainability and separation of concerns.

Usage:
    from api.services.email_service import EmailService
    
    service = EmailService(request=request)
    service.send_welcome_email(user)
    service.send_password_reset_email(user, reset_url)
"""

from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.translation import gettext as _
from typing import List, Optional
import logging
import os
import base64
from pathlib import Path

logger = logging.getLogger(__name__)


class EmailService:
    """Service class for handling all email operations in the AWN Platform."""
    
    DEFAULT_FROM_EMAIL = settings.DEFAULT_FROM_EMAIL
    PLATFORM_URL = getattr(settings, 'PLATFORM_URL', 'https://awn-three.vercel.app')
    
    def __init__(self, request=None):
        """
        Initialize the email service.
        
        Args:
            request: Django request object for building absolute URLs
        """
        self.request = request
    
    def _get_logo_url(self) -> str:
        """
        Get the absolute URL for the platform logo.
        Prioritizes PLATFORM_URL for production deployment.
        """
        # Use PLATFORM_URL for deployed environments (primary method for production)
        platform_url = getattr(settings, 'PLATFORM_URL', None)
        if platform_url:
            if platform_url.endswith('/'):
                platform_url = platform_url[:-1]
            # For Vercel/production deployments
            return f"{platform_url}/media/awnlogo.png"
        
        # Try to build from request (for API calls with request context)
        if self.request:
            try:
                media_url = getattr(settings, 'MEDIA_URL', '/media/')
                logo_path = f"{media_url}awnlogo.png".replace('//', '/')
                return self.request.build_absolute_uri(logo_path)
            except Exception:
                pass
        
        # Fallback to BASE_URL
        base_url = getattr(settings, 'BASE_URL', None)
        if base_url:
            if base_url.endswith('/'):
                base_url = base_url[:-1]
            media_url = getattr(settings, 'MEDIA_URL', '/media/')
            if not media_url.startswith('/'):
                media_url = '/' + media_url
            logo_path = f"{media_url}awnlogo.png".replace('//', '/')
            return f"{base_url}{logo_path}"
        
        # Last resort: Use your deployed URL directly
        return "https://par.infnet.tech:8001/media/awnlogo.png"
    
    def _get_logo_base64(self) -> Optional[str]:
        """
        Get the logo as base64 encoded string for embedding in emails.
        DISABLED: Using logo URL instead to keep email size small.
        
        Returns:
            None (base64 encoding disabled)
        """
        # Base64 encoding disabled to reduce email size
        # Gmail clips emails larger than 102KB
        # Logo URL is more efficient and works well for production
        return None
    
    def _render_email_template(self, template_name: str, context: dict) -> tuple:
        """
        Render an email template with the given context.
        
        Args:
            template_name: Name of the template (without .html extension)
            context: Dictionary of context variables
            
        Returns:
            Tuple of (html_content, plain_text_content)
        """
        # Add common context variables - prioritize URL over base64 for smaller emails
        context.setdefault('logo_url', self._get_logo_url())
        # Don't include base64 logo - it makes emails too large (>1MB)
        # Gmail will show "view entire message" for emails > 102KB
        context.setdefault('logo_base64', None)
        context.setdefault('platform_url', self.PLATFORM_URL)
        
        # Render HTML version
        html_content = render_to_string(
            f'emails/{template_name}.html',
            context,
            request=self.request
        )
        
        # Create plain text version by stripping HTML tags
        plain_text = strip_tags(html_content)
        
        return html_content, plain_text
    
    def _send_email(
        self,
        subject: str,
        to_emails: List[str],
        html_content: str,
        plain_text: str,
        fail_silently: bool = True,
        reply_to: Optional[List[str]] = None
    ) -> bool:
        """
        Send an email with both HTML and plain text versions.
        
        Args:
            subject: Email subject
            to_emails: List of recipient email addresses
            html_content: HTML version of the email
            plain_text: Plain text version of the email
            fail_silently: Whether to suppress exceptions
            reply_to: Optional reply-to addresses
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        try:
            email = EmailMultiAlternatives(
                subject=subject,
                body=plain_text,
                from_email=self.DEFAULT_FROM_EMAIL,
                to=to_emails,
                reply_to=reply_to or ['no-reply@awnpaltform.gmail.com'],
                headers={
                    'X-Entity-Type': 'Transactional',
                }
            )
            email.attach_alternative(html_content, "text/html")
            result = email.send(fail_silently=False)
            
            if result == 0:
                logger.warning(f"Email send returned 0 for recipients: {to_emails}")
                return False
            
            logger.info(f"Email sent successfully to {to_emails}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_emails}: {str(e)}")
            if not fail_silently:
                raise
            return False
    
    # =========================================================================
    # User-related emails
    # =========================================================================
    
    def send_welcome_email(
        self,
        user,
        is_organization: bool = False,
        fail_silently: bool = True
    ) -> bool:
        """
        Send welcome email to a newly registered user or organization.
        
        Args:
            user: User model instance
            is_organization: Whether the user is an organization
            fail_silently: Whether to suppress exceptions
            
        Returns:
            True if email was sent successfully
        """
        subject = _("Welcome to AWN Platform!")
        user_name = user.name if hasattr(user, 'name') else user.email
        
        if is_organization and hasattr(user, 'organization') and user.organization:
            user_name = user.organization.name
        
        context = {
            'user_name': user_name,
            'user_email': user.email,
            'is_organization': is_organization,
            'cta_url': f"{self.PLATFORM_URL}/login",
            'cta_label': _("Get Started"),
        }
        
        html_content, plain_text = self._render_email_template('welcome', context)
        
        return self._send_email(
            subject=subject,
            to_emails=[user.email],
            html_content=html_content,
            plain_text=plain_text,
            fail_silently=fail_silently
        )
    
    def send_password_reset_email(
        self,
        user,
        reset_url: str,
        fail_silently: bool = False
    ) -> bool:
        """
        Send password reset email with reset link.
        
        Args:
            user: User model instance
            reset_url: Password reset URL
            fail_silently: Whether to suppress exceptions
            
        Returns:
            True if email was sent successfully
        """
        subject = _("Reset Your AWN Platform Password")
        user_name = user.name if hasattr(user, 'name') else user.email
        
        context = {
            'user_name': user_name,
            'user_email': user.email,
            'reset_url': reset_url,
        }
        
        html_content, plain_text = self._render_email_template('password_reset', context)
        
        return self._send_email(
            subject=subject,
            to_emails=[user.email],
            html_content=html_content,
            plain_text=plain_text,
            fail_silently=fail_silently
        )
    
    # =========================================================================
    # Support-related emails
    # =========================================================================
    
    def send_support_received_email(
        self,
        support_request,
        fail_silently: bool = True
    ) -> bool:
        """
        Send confirmation email when a support request is received.
        
        Args:
            support_request: HelpSupport model instance
            fail_silently: Whether to suppress exceptions
            
        Returns:
            True if email was sent successfully
        """
        subject = _("Support Request Received")
        user_name = support_request.user.name or support_request.user.email
        
        context = {
            'user_name': user_name,
            'user_email': support_request.user.email,
            'request_title': support_request.title,
            'request_id': support_request.id,
            'request_type': support_request.get_type_display(),
            'cta_url': f"{self.PLATFORM_URL}/support/requests",
        }
        
        html_content, plain_text = self._render_email_template('support_received', context)
        
        return self._send_email(
            subject=subject,
            to_emails=[support_request.user.email],
            html_content=html_content,
            plain_text=plain_text,
            fail_silently=fail_silently
        )
    
    def send_support_reply_email(
        self,
        support_request,
        reply_text: str,
        fail_silently: bool = True
    ) -> bool:
        """
        Send email notification when support team replies to a request.
        
        Args:
            support_request: HelpSupport model instance
            reply_text: The reply message text
            fail_silently: Whether to suppress exceptions
            
        Returns:
            True if email was sent successfully
        """
        subject = _("Response to Your Support Request: {title}").format(
            title=support_request.title
        )
        user_name = support_request.user.name or support_request.user.email
        
        context = {
            'user_name': user_name,
            'user_email': support_request.user.email,
            'request_title': support_request.title,
            'request_id': support_request.id,
            'reply_text': reply_text,
            'cta_url': f"{self.PLATFORM_URL}/support/requests",
        }
        
        html_content, plain_text = self._render_email_template('support_reply', context)
        
        return self._send_email(
            subject=subject,
            to_emails=[support_request.user.email],
            html_content=html_content,
            plain_text=plain_text,
            fail_silently=fail_silently
        )
    
    def send_admin_support_notification(
        self,
        support_request,
        admin_emails: List[str],
        fail_silently: bool = True
    ) -> bool:
        """
        Send notification to admins about a new support request.
        
        Args:
            support_request: HelpSupport model instance
            admin_emails: List of admin email addresses
            fail_silently: Whether to suppress exceptions
            
        Returns:
            True if email was sent successfully
        """
        subject = _("New Support Request: {title}").format(
            title=support_request.title
        )
        
        context = {
            'request_title': support_request.title,
            'request_type': support_request.get_type_display(),
            'request_id': support_request.id,
            'request_description': support_request.description,
            'user_name': support_request.user.name or 'N/A',
            'user_email': support_request.user.email,
            'cta_url': f"{self.PLATFORM_URL}/admin/support",
        }
        
        html_content, plain_text = self._render_email_template(
            'admin_support_notification',
            context
        )
        
        return self._send_email(
            subject=subject,
            to_emails=admin_emails,
            html_content=html_content,
            plain_text=plain_text,
            fail_silently=fail_silently
        )
    
    # =========================================================================
    # Notification emails
    # =========================================================================
    
    def send_notification_email(
        self,
        to_email: str,
        title: str,
        message: str,
        cta_url: Optional[str] = None,
        cta_label: Optional[str] = None,
        reply_html: Optional[str] = None,
        signoff_text: Optional[str] = None,
        fail_silently: bool = True
    ) -> bool:
        """
        Send a generic notification email.
        
        Args:
            to_email: Recipient email address
            title: Email title
            message: Email message content
            cta_url: Optional call-to-action URL
            cta_label: Optional call-to-action button label
            reply_html: Optional additional reply/info HTML
            signoff_text: Optional custom signoff text
            fail_silently: Whether to suppress exceptions
            
        Returns:
            True if email was sent successfully
        """
        context = {
            'title': title,
            'message': message,
            'cta_url': cta_url,
            'cta_label': cta_label,
            'reply_html': reply_html,
            'signoff_text': signoff_text or _('AWN Platform'),
        }
        
        html_content, plain_text = self._render_email_template('notification', context)
        
        return self._send_email(
            subject=title,
            to_emails=[to_email],
            html_content=html_content,
            plain_text=plain_text,
            fail_silently=fail_silently
        )
    
    def send_bulk_notification_email(
        self,
        recipients: List[str],
        title: str,
        message: str,
        cta_url: Optional[str] = None,
        cta_label: Optional[str] = None,
        fail_silently: bool = True
    ) -> int:
        """
        Send notification email to multiple recipients.
        
        Args:
            recipients: List of recipient email addresses
            title: Email title
            message: Email message content
            cta_url: Optional call-to-action URL
            cta_label: Optional call-to-action button label
            fail_silently: Whether to suppress exceptions
            
        Returns:
            Number of successfully sent emails
        """
        success_count = 0
        
        for email in recipients:
            if not email:
                continue
                
            if self.send_notification_email(
                to_email=email,
                title=title,
                message=message,
                cta_url=cta_url,
                cta_label=cta_label,
                fail_silently=fail_silently
            ):
                success_count += 1
        
        logger.info(f"Sent {success_count}/{len(recipients)} bulk notification emails")
        return success_count
    
    # =========================================================================
    # Announcement-related emails
    # =========================================================================
    
    def send_announcement_approved_email(
        self,
        announcement,
        recipient_email: str,
        fail_silently: bool = True
    ) -> bool:
        """
        Send email notification when a new announcement is approved.
        
        Args:
            announcement: Announcement model instance
            recipient_email: Recipient email address
            fail_silently: Whether to suppress exceptions
            
        Returns:
            True if email was sent successfully
        """
        subject = _("New Announcement: {title}").format(title=announcement.title)
        
        context = {
            'announcement_title': announcement.title,
            'announcement_description': announcement.description[:200] + '...' if len(announcement.description) > 200 else announcement.description,
            'organization_name': announcement.organization_name or (announcement.organization.user.name if announcement.organization else 'AWN Platform'),
            'cta_url': f"{self.PLATFORM_URL}/announcements/{announcement.id}",
            'cta_label': _("View Announcement"),
        }
        
        html_content, plain_text = self._render_email_template('announcement_approved', context)
        
        return self._send_email(
            subject=subject,
            to_emails=[recipient_email],
            html_content=html_content,
            plain_text=plain_text,
            fail_silently=fail_silently
        )
    
    def send_announcement_status_email(
        self,
        announcement,
        recipient_email: str,
        status: str,
        admin_notes: str = None,
        fail_silently: bool = True
    ) -> bool:
        """
        Send email notification when announcement status changes.
        
        Args:
            announcement: Announcement model instance
            recipient_email: Recipient email address
            status: New status (approved, rejected, etc.)
            admin_notes: Optional admin notes
            fail_silently: Whether to suppress exceptions
            
        Returns:
            True if email was sent successfully
        """
        status_display = status.title()
        subject = _("{status}: {title}").format(status=status_display, title=announcement.title)
        
        context = {
            'announcement_title': announcement.title,
            'status': status_display,
            'admin_notes': admin_notes,
            'cta_url': f"{self.PLATFORM_URL}/my-announcements",
            'cta_label': _("View My Announcements"),
        }
        
        html_content, plain_text = self._render_email_template('announcement_status', context)
        
        return self._send_email(
            subject=subject,
            to_emails=[recipient_email],
            html_content=html_content,
            plain_text=plain_text,
            fail_silently=fail_silently
        )
