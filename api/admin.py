from django.contrib import admin
from django.utils import timezone
from .models import (
    User, Announcement, AnnouncementCategory,
    UserFavorite, Organization, OrganizationDocument,
    Notification, HelpSupport, AnnouncementEditRequest
)

# ----- User -----
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "role", "is_active", "created_at", "updated_at")
    list_filter = ("role", "is_active")
    search_fields = ("name", "email")
    readonly_fields = ("created_at", "updated_at", "last_login")


# ----- Announcement -----
@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "organization", "status", "start_date", "end_date", "created_at", "updated_at")
    list_filter = ("status", "organization")
    search_fields = ("title", "description")
    readonly_fields = ("created_at", "updated_at")
    actions = ['approve_announcements', 'reject_announcements']
    
    def approve_announcements(self, request, queryset):
        """Admin action to approve selected announcements"""
        updated = queryset.update(status='approved')
        self.message_user(request, f'{updated} announcements were successfully approved.')
    approve_announcements.short_description = "Approve selected announcements"
    
    def reject_announcements(self, request, queryset):
        """Admin action to reject selected announcements"""
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} announcements were successfully rejected.')
    reject_announcements.short_description = "Reject selected announcements"
    
    def get_queryset(self, request):
        """Show all announcements to admin, with pending ones highlighted"""
        qs = super().get_queryset(request)
        # Admin can see all announcements, but we can order by status to show pending first
        return qs.order_by('status', '-created_at')

# ----- AnnouncementCategory -----
@admin.register(AnnouncementCategory)
class AnnouncementCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)

# ----- AnnouncementEditRequest -----
@admin.register(AnnouncementEditRequest)
class AnnouncementEditRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "original_announcement", "requested_by", "status", "created_at", "reviewed_at")
    list_filter = ("status", "created_at", "reviewed_at")
    search_fields = ("original_announcement__title", "requested_by__name", "requested_by__email")
    readonly_fields = ("created_at", "updated_at", "reviewed_by", "reviewed_at")
    actions = ['approve_edit_requests', 'reject_edit_requests']
    
    def approve_edit_requests(self, request, queryset):
        """Admin action to approve selected edit requests"""
        approved_count = 0
        for edit_request in queryset.filter(status='pending'):
            edit_request.status = 'approved'
            edit_request.reviewed_by = request.user
            edit_request.reviewed_at = timezone.now()
            edit_request.save()
            
            # Apply changes to the original announcement
            edit_request.apply_changes()
            approved_count += 1
        
        self.message_user(request, f'{approved_count} edit requests were successfully approved and applied.')
    approve_edit_requests.short_description = "Approve selected edit requests"
    
    def reject_edit_requests(self, request, queryset):
        """Admin action to reject selected edit requests"""
        rejected_count = 0
        for edit_request in queryset.filter(status='pending'):
            edit_request.status = 'rejected'
            edit_request.reviewed_by = request.user
            edit_request.reviewed_at = timezone.now()
            edit_request.save()
            rejected_count += 1
        
        self.message_user(request, f'{rejected_count} edit requests were successfully rejected.')
    reject_edit_requests.short_description = "Reject selected edit requests"
    
    def get_queryset(self, request):
        """Show pending edit requests first"""
        qs = super().get_queryset(request)
        return qs.order_by('status', '-created_at')

# Application admin removed - announcements handle their own status workflow
# Users view approved announcements and apply through external URLs

# ----- UserFavorite -----
@admin.register(UserFavorite)
class UserFavoriteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",               # الشخص الذي أضاف الـ favorite
        "get_announcement_user", # صاحب الإعلان
        "get_announcement",
        "created_at",
        "updated_at"
    )
    search_fields = ("user__name", "announcement__title", "announcement__organization__user__name")
    readonly_fields = ("created_at", "updated_at")

    def get_announcement_user(self, obj):
        # صاحب الإعلان
        return obj.announcement.organization.user.name or obj.announcement.organization.user.email
    get_announcement_user.short_description = "Announcement Owner"

    def get_announcement(self, obj):
        return obj.announcement.title
    get_announcement.short_description = "Announcement"

# ----- Organization -----
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "verified", "is_active", "is_rejected", "rate", "created_at", "updated_at"
    )
    list_filter = ("verified", "is_active", "is_rejected")
    search_fields = ("description", "rejection_reason", "user__name", "user__email")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {
            "fields": ("user", "description", "website", "location", "rate")
        }),
        ("Status", {
            "fields": ("verified", "is_active", "is_rejected", "rejection_reason")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )


# ----- OrganizationDocument -----
@admin.register(OrganizationDocument)
class OrganizationDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "organization", "created_at")
    readonly_fields = ("created_at",)

# ----- Notification -----
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "shown", "created_at")
    list_filter = ("shown",)
    search_fields = ("user__name", "title", "message")
    readonly_fields = ("created_at", "updated_at")

# ----- Review -----
# Review admin removed - dependent on Application model which was removed
    
# ----- HelpSupport -----
@admin.register(HelpSupport)
class HelpSupportAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "type", "status", "target_org", 
        "priority", "created_at"
    )
    list_filter = ("type", "status", "priority", "created_at")
    search_fields = ("user__name", "description", "target_org__user__name")
    readonly_fields = ("created_at",)

    fieldsets = (
        ("User Info", {
            "fields": ("user", "type", "description")
        }),
        ("Complaint Details", {
            "fields": ("target_org", "priority")
        }),
        ("Status & Response", {
            "fields": ("status", "admin_response")
        }),
        ("Metadata", {
            "fields": ("created_at",)
        }),
    )