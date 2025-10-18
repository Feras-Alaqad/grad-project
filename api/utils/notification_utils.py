"""
Notification and Email Utility Module

This module provides utilities for creating in-app notifications and sending emails together.
Ensures every email sent is also recorded as an in-app notification.

Usage:
    from api.utils.notification_utils import NotificationManager
    
    manager = NotificationManager(request)
    manager.notify_and_email_user(user, title, message)
"""

from django.conf import settings
from api.models import Notification, User
from api.services.email_service import EmailService
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class NotificationManager:
    """Manager for creating notifications and sending emails together."""
    
    def __init__(self, request=None):
        """
        Initialize the notification manager.
        
        Args:
            request: Django request object for building absolute URLs
        """
        self.request = request
        self.email_service = EmailService(request)
    
    def notify_user(
        self,
        user,
        title: str,
        message: str,
        email: bool = True,
        cta_url: Optional[str] = None,
        cta_label: Optional[str] = None
    ) -> Notification:
        """
        Create an in-app notification and optionally send email.
        
        Args:
            user: User model instance
            title: Notification title
            message: Notification message
            email: Whether to also send email
            cta_url: Optional call-to-action URL
            cta_label: Optional call-to-action button label
            
        Returns:
            Created Notification instance
        """
        # Create in-app notification
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message
        )
        
        # Send email if requested
        if email and user.email:
            try:
                self.email_service.send_notification_email(
                    to_email=user.email,
                    title=title,
                    message=message,
                    cta_url=cta_url,
                    cta_label=cta_label,
                    fail_silently=True
                )
            except Exception as e:
                logger.error(f"Failed to send email to {user.email}: {str(e)}")
        
        return notification
    
    def notify_users_bulk(
        self,
        users: List[User],
        title: str,
        message: str,
        email: bool = True,
        cta_url: Optional[str] = None,
        cta_label: Optional[str] = None
    ) -> List[Notification]:
        """
        Create in-app notifications for multiple users and optionally send emails.
        
        Args:
            users: List of User model instances
            title: Notification title
            message: Notification message
            email: Whether to also send emails
            cta_url: Optional call-to-action URL
            cta_label: Optional call-to-action button label
            
        Returns:
            List of created Notification instances
        """
        notifications = []
        
        # Create in-app notifications
        for user in users:
            notification = Notification.objects.create(
                user=user,
                title=title,
                message=message
            )
            notifications.append(notification)
        
        # Send emails if requested
        if email:
            recipient_emails = [user.email for user in users if user.email]
            if recipient_emails:
                try:
                    self.email_service.send_bulk_notification_email(
                        recipients=recipient_emails,
                        title=title,
                        message=message,
                        cta_url=cta_url,
                        cta_label=cta_label,
                        fail_silently=True
                    )
                except Exception as e:
                    logger.error(f"Failed to send bulk emails: {str(e)}")
        
        return notifications
    
    def notify_announcement_approved(
        self,
        announcement,
        users: List[User]
    ) -> List[Notification]:
        """
        Notify users about a newly approved announcement.
        Creates in-app notifications and sends emails.
        
        Args:
            announcement: Announcement model instance
            users: List of User model instances to notify
            
        Returns:
            List of created Notification instances
        """
        title = f"New Announcement: {announcement.title}"
        message = f"A new announcement '{announcement.title}' has been added to the platform."
        
        notifications = []
        
        # Create in-app notifications
        for user in users:
            notification = Notification.objects.create(
                user=user,
                title=title,
                message=message
            )
            notifications.append(notification)
        
        # Send emails
        for user in users:
            if not user.email:
                continue
            try:
                self.email_service.send_announcement_approved_email(
                    announcement=announcement,
                    recipient_email=user.email,
                    fail_silently=True
                )
            except Exception as e:
                logger.error(f"Failed to send announcement email to {user.email}: {str(e)}")
        
        logger.info(f"Notified {len(notifications)} users about announcement: {announcement.title}")
        return notifications
    
    def notify_announcement_status_change(
        self,
        announcement,
        organization_user,
        status: str,
        admin_notes: str = None
    ) -> Notification:
        """
        Notify organization about announcement status change.
        Creates in-app notification and sends email.
        
        Args:
            announcement: Announcement model instance
            organization_user: Organization user to notify
            status: New status (approved, rejected, etc.)
            admin_notes: Optional admin notes
            
        Returns:
            Created Notification instance
        """
        status_display = status.title()
        title = f"{status_display}: {announcement.title}"
        message = admin_notes or f"Your announcement '{announcement.title}' was {status_display.lower()} by admin."
        
        # Create in-app notification
        notification = Notification.objects.create(
            user=organization_user,
            title=title,
            message=message
        )
        
        # Send email
        if organization_user.email:
            try:
                self.email_service.send_announcement_status_email(
                    announcement=announcement,
                    recipient_email=organization_user.email,
                    status=status,
                    admin_notes=admin_notes,
                    fail_silently=True
                )
            except Exception as e:
                logger.error(f"Failed to send status email to {organization_user.email}: {str(e)}")
        
        return notification
    
    def notify_welcome(
        self,
        user,
        is_organization: bool = False
    ) -> Notification:
        """
        Send welcome notification to new user.
        Creates in-app notification and sends email.
        
        Args:
            user: User model instance
            is_organization: Whether the user is an organization
            
        Returns:
            Created Notification instance
        """
        title = "Welcome to AWN Platform!"
        message = "Thank you for joining AWN Platform! You can now explore announcements and connect with organizations."
        
        # Create in-app notification
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message
        )
        
        # Send welcome email
        try:
            self.email_service.send_welcome_email(
                user=user,
                is_organization=is_organization,
                fail_silently=True
            )
        except Exception as e:
            logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
        
        return notification
    
    def notify_support_received(
        self,
        support_request
    ) -> Notification:
        """
        Notify user that their support request was received.
        Creates in-app notification and sends email.
        
        Args:
            support_request: HelpSupport model instance
            
        Returns:
            Created Notification instance
        """
        title = f"Support Ticket Received: {support_request.title}"
        message = "We have received your support request and will respond soon."
        
        # Create in-app notification
        notification = Notification.objects.create(
            user=support_request.user,
            title=title,
            message=message
        )
        
        # Send email
        try:
            self.email_service.send_support_received_email(
                support_request=support_request,
                fail_silently=True
            )
        except Exception as e:
            logger.error(f"Failed to send support email to {support_request.user.email}: {str(e)}")
        
        return notification
    
    def notify_support_reply(
        self,
        support_request,
        reply_text: str
    ) -> Notification:
        """
        Notify user that their support request received a reply.
        Creates in-app notification and sends email.
        
        Args:
            support_request: HelpSupport model instance
            reply_text: Reply message text
            
        Returns:
            Created Notification instance
        """
        title = f"Support Reply: {support_request.title}"
        message = reply_text
        
        # Create in-app notification
        notification = Notification.objects.create(
            user=support_request.user,
            title=title,
            message=message
        )
        
        # Send email
        try:
            self.email_service.send_support_reply_email(
                support_request=support_request,
                reply_text=reply_text,
                fail_silently=True
            )
        except Exception as e:
            logger.error(f"Failed to send reply email to {support_request.user.email}: {str(e)}")
        
        return notification
