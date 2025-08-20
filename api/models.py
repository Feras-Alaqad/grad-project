from django.contrib.auth.models import AbstractUser, BaseUserManager

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator


class UserManager(BaseUserManager):
    """
    Custom user manager - uses email instead of username
    """
    def create_user(self, email, password=None, **extra_fields):
        """Create a regular user"""
        if not email:
            raise ValueError('Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create a superuser (admin)"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True or extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_staff=True and is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    """
    Custom user model
    - Uses email instead of username
    - Contains different roles (institution, admin, user)
    """
    class Role(models.TextChoices):
        ORGANIZATION = "organization", "Organization"
        ADMIN = "admin", "Admin"
        USER = "user", "User"

    # Remove username and use email
    username = None
    first_name = None
    last_name = None
    name = models.CharField(
        max_length=255, 
        blank=True,
        verbose_name="Name",
        help_text="Full user name"
    )
    email = models.EmailField(
        unique=True,
        verbose_name="Email",
        help_text="Unique email address for the user"
    )
    phone = models.CharField(
        max_length=14,
        blank=True,
        verbose_name="Phone Number",
        help_text="User's phone number"
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name="Active",
        help_text="Is the user active?"
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
        verbose_name="Role",
        help_text="User role in the system"
    )
    date_joined = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date Joined",
        help_text="Date when the user joined"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creation Date",
        help_text="Date when the user was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Update Date",
        help_text="Date when the user was last updated"
    )
    
    # Set email as the primary login field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'password', 'role', 'phone']
    
    objects = UserManager()

    def __str__(self):
        return f"{self.name or self.email} ({self.get_role_display()})"

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

class AnnouncementCategory(models.Model):
    """
    Announcement categories model
    - Allows categorization of announcements
    - Supports hierarchical categories
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Category Name",
        help_text="Unique name for the announcement category"
    )


class Announcement(models.Model):
    """
    Main announcements model
    - Contains all basic information for the announcement
    - Supports different statuses and various categories
    - Linked to author and tracks views
    """
    
    class Status(models.TextChoices):
        PENDING = "pending", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        DRAFT = "draft", "Draft"
    
    # Basic fields
    title = models.CharField(
        max_length=255,
        verbose_name="Title",
        help_text="Announcement title"
    )
    description = models.TextField(
        verbose_name="Description",
        help_text="Detailed description of the announcement"
    )
    start_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Start Date",
        help_text="Announcement start date (optional)"
    )
    end_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="End Date",
        help_text="Announcement end date (optional)"
    )
    organization = models.ForeignKey(
        'Organization',  # Use string to reference model defined later
        on_delete=models.CASCADE,
        related_name='announcements',
        null=True,
        blank=True,
        verbose_name="Organization",
        help_text="Organization the announcement belongs to (optional)"
    )
    organization_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Organization Name",
        help_text="Custom organization name (for admin use)"
    )
    url = models.URLField(
        blank=False,
        null=False,
        verbose_name="URL",
        help_text="Link to the announcement details",
        default="https://example.com"  # ضع الرابط الافتراضي هنا
    )
    category = models.ForeignKey(
        'AnnouncementCategory',
        on_delete=models.CASCADE,
        related_name='announcements',
        verbose_name="Category",
        help_text="Announcement category",
        default=1
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Status",
        help_text="Announcement approval status"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_announcements',
        verbose_name="Created By",
        help_text="User who created this announcement",
        default=1
    )
    admin_notes = models.TextField(
        blank=True,
        verbose_name="Admin Notes",
        help_text="Admin notes about the announcement approval/rejection"
    )

   
    # Automatic timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Creation Date"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Update Date"
    )
    REQUIRED_FIELDS = ['title', 'description', 'url']

    def __str__(self):
        return self.title

    def clean(self):
        """Data validation"""
        if self.expiry_date and self.publish_date:
            if self.expiry_date <= self.publish_date:
                raise ValidationError('Expiry date must be after publish date')
    

    class Meta:
        verbose_name = "Announcement"
        verbose_name_plural = "Announcements"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
        ]

class Application(models.Model):
    """
    Applications model for announcement applications
    - Links user and announcement
    - Tracks application status and admin notes
    - Prevents duplicate applications from same user to same announcement
    """
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        IN_REVIEW = "in_review", "In Review"
        WITHDRAWN = "withdrawn", "Withdrawn"

    # Basic relationships
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name="Announcement",
        help_text="Announcement being applied to"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name="User",
        help_text="User applying"
    )
    
    # Application status and notes
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Status",
        help_text="Application status"
    )
    admin_notes = models.TextField(
        blank=True,
        verbose_name="Admin Notes",
        help_text="Admin notes about the application"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Application Date"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Update Date"
    )

    def __str__(self):
        return f"{self.user.name or self.user.email} - {self.announcement.title} - {self.get_status_display()}"

    class Meta:
        verbose_name = "Application"
        verbose_name_plural = "Applications"
        # Prevent duplicate applications from same user to same announcement
        constraints = [
            models.UniqueConstraint(
                fields=['announcement', 'user'], 
                name='unique_application'
            )
        ]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['user', 'status']),
        ]


class UserFavorite(models.Model):
    """
    User favorites model
    - Allows users to add announcements to favorites
    - Many-to-many relationship between users and announcements
    - Prevents adding same announcement to favorites more than once
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name="User",
        help_text="User who added announcement to favorites"
    )
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name="Announcement",
        help_text="Announcement added to favorites"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Addition Date",
        help_text="Date announcement was added to favorites"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Update Date",
        help_text="Date when favorite was last updated"
    )

    def __str__(self):
        return f"{self.user.name or self.user.email} - {self.announcement.title}"

    class Meta:
        verbose_name = "Favorite"
        verbose_name_plural = "Favorites"
        # Prevent adding same announcement to favorites more than once by same user
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'announcement'], 
                name='unique_user_favorite'
            )
        ]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

class Organization(models.Model):
    """
    Organizations/Institutions model
    - Contains information about different organizations
    - Linked to users and announcements
    - Includes verification and rating information
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='organizations',
        verbose_name="Responsible User",
        help_text="User responsible for the organization"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Organization Description",
        help_text="Detailed description of organization and its activities"
    )
    website = models.URLField(
        blank=True,
        verbose_name="Website",
        help_text="Organization's official website link"
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Location",
        help_text="Organization's address or geographical location"
    )
    rate = models.PositiveSmallIntegerField(
    validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    verified = models.BooleanField(
        default=False,
        verbose_name="Verified",
        help_text="Is the organization verified by admin?"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Active",
        help_text="Is the organization currently active?"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Registration Date"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Update Date"
    )

    def __str__(self):
        return self.user.name or self.user.email

    def clean(self):
        """Validate rate"""
        if self.rate < 1 or self.rate > 5:
            raise ValidationError('Rate must be between 1 and 5')
        

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"
        ordering = ['-rate', '-created_at']
        indexes = [
            models.Index(fields=['verified', 'is_active']),
            models.Index(fields=['-rate']),
        ]


class OrganizationDocument(models.Model):
    """
    Organization documents model
    - Contains all documents required for organization verification
    - Supports different types of documents
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name="Organization"
    )
    registration_docs = models.FileField(
        upload_to='organizations/registration/',
        blank=True,
        verbose_name="Registration Documents",
        help_text="Official organization registration documents"
    )
    financial_report = models.FileField(
        upload_to='organizations/financial/',
        blank=True,
        verbose_name="Financial Report",
        help_text="Organization financial reports"
    )
    activity_proof = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Activity Proof",
        help_text="JSON data containing organization activity proofs"
    )
    address_proof = models.FileField(
        upload_to='organizations/address/',
        blank=True,
        verbose_name="Financial Report",
        help_text="Organization financial reports"
    )

    created_at = models.DateTimeField(default=timezone.now)


    def __str__(self):
        return f"{self.organization.name} Documents"

    class Meta:
        verbose_name = "Organization Document"
        verbose_name_plural = "Organization Documents"


class Notification(models.Model):
    """
    Notifications model
    - Sends notifications to users about various events
    - Supports read/unread notification states
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="User",
        help_text="User receiving the notification"
    )
    title = models.CharField(
        max_length=50,
        blank=False,
        default="Notification",
    )
    message = models.TextField(
        verbose_name="Notification Message",
        help_text="Notification text sent to user"
    )
    read_status = models.BooleanField(
        default=False,
        verbose_name="Read Status",
        help_text="Has the notification been read?"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Send Date"
    )

    def __str__(self):
        status = "Read" if self.read_status else "Unread"
        return f"Notification to {self.user.name or self.user.email} - {status}"

    def mark_as_read(self):
        """Mark notification as read"""
        self.read_status = True
        self.save()

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'read_status']),
            models.Index(fields=['-created_at']),
        ]


class Review(models.Model):
    """
    Reviews and ratings model
    - Allows users to rate applications
    - Contains comments and numerical rating
    """
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name="Application",
        help_text="Application to be reviewed"
    )
    comment = models.TextField(
        blank=True,
        verbose_name="Comment",
        help_text="Comment or notes about the application"
    )
    rating = models.PositiveSmallIntegerField(
    validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    created_at = models.DateTimeField(default=timezone.now)


    def __str__(self):
        return f"Review for {self.application.user.name} application - {self.rating}/5"

    def clean(self):
        """Validate rating"""
        if self.rating < 1 or self.rating > 5:
            raise ValidationError('Rating must be between 1 and 5')

    class Meta:
        verbose_name = "Review"
        verbose_name_plural = "Reviews"
        # Prevent reviewing same application more than once by same reviewer
        constraints = [
            models.UniqueConstraint(
                fields=['application'], 
                name='unique_application_review'
            )
        ]


class HelpSupport(models.Model):
    """
    Help and support model
    - Allows users to send support requests
    - Supports different types of support requests
    """
    class SupportType(models.TextChoices):
        ACCOUNT = "account", "Account Issue"
        GENERAL = "general", "General Inquiry"
        COMPLAINT = "complaint", "Complaint"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='support_requests',
        verbose_name="User",
        help_text="User who sent the support request"
    )
    description = models.TextField(
        verbose_name="Issue Description",
        help_text="Detailed description of the issue or inquiry"
    )
    type = models.CharField(
        max_length=20,
        choices=SupportType.choices,
        default=SupportType.GENERAL,
        verbose_name="Request Type",
        help_text="Type of support request"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Send Date"
    )

    def __str__(self):
        return f"Support request from {self.user.name or self.user.email} - {self.get_type_display()}"

    class Meta:
        verbose_name = "Support Request"
        verbose_name_plural = "Support Requests"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['type', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]