from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
from api.models import UserApplicationTracking, Notification


class Command(BaseCommand):
    help = 'Send reminder notifications for upcoming application deadlines'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=1,
            help='Number of days ahead to check for reminders (default: 1)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending'
        )

    def handle(self, *args, **options):
        days_ahead = options['days_ahead']
        dry_run = options['dry_run']
        
        # Calculate the target date for reminders
        target_date = timezone.now().date() + timedelta(days=days_ahead)
        
        # Find all tracking entries with reminder_date matching target date
        upcoming_reminders = UserApplicationTracking.objects.filter(
            reminder_date=target_date
        ).select_related('user', 'announcement')
        
        if not upcoming_reminders.exists():
            self.stdout.write(
                self.style.SUCCESS(f'No reminders found for {target_date}')
            )
            return
        
        sent_count = 0
        error_count = 0
        
        for tracking in upcoming_reminders:
            try:
                if dry_run:
                    self.stdout.write(
                        f'Would send reminder to {tracking.user.email} for '
                        f'announcement: {tracking.announcement.title}'
                    )
                else:
                    # Send email notification
                    self._send_email_notification(tracking)
                    
                    # Create in-app notification
                    self._create_in_app_notification(tracking)
                    
                    self.stdout.write(
                        f'Sent reminder to {tracking.user.email} for '
                        f'announcement: {tracking.announcement.title}'
                    )
                
                sent_count += 1
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed to send reminder to {tracking.user.email}: {str(e)}'
                    )
                )
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Dry run completed. Would send {sent_count} reminders.'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Sent {sent_count} reminders successfully. '
                    f'{error_count} errors occurred.'
                )
            )
    
    def _send_email_notification(self, tracking):
        """Send email notification for reminder"""
        subject = f'Reminder: {tracking.announcement.title}'
        
        message = f"""
Hello {tracking.user.first_name or tracking.user.email},

This is a reminder about the announcement: {tracking.announcement.title}
Organization: {tracking.announcement.organization_name}

Your current status: {tracking.get_status_display()}

{f'Your notes: {tracking.notes}' if tracking.notes else ''}

Please check the announcement for any updates or deadlines.

Best regards,
AWN Team
        """.strip()
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[tracking.user.email],
            fail_silently=False
        )
    
    def _create_in_app_notification(self, tracking):
        """Create in-app notification for reminder"""
        Notification.objects.create(
            user=tracking.user,
            title=f'Reminder: {tracking.announcement.title}',
            message=f'Don\'t forget about the announcement from {tracking.announcement.organization_name}. '
                   f'Your current status: {tracking.get_status_display()}'
        )