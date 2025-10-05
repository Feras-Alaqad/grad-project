from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.conf import settings
import os
from .forms import UserAdminCreationForm, UserAdminChangeForm
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import (
    User, Announcement, AnnouncementCategory,
    UserFavorite, Organization, OrganizationDocument,
    Notification, HelpSupport
)

# ----- User -----
class UserAdmin(BaseUserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm

    list_display = ("id", "profile_image_tag", "name", "email", "role", "is_active", "created_at", "updated_at")
    list_filter = ("role", "is_active")
    search_fields = ("name", "email")
    readonly_fields = ("created_at", "updated_at", "last_login")

    ordering = ("-created_at",) 

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('name', 'phone', 'profile_image')}),
        ('Permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'phone', 'role', 'password', 'is_active', 'is_staff', 'is_superuser')}
        ),
    )

    def profile_image_tag(self, obj):
        if obj.profile_image and os.path.exists(obj.profile_image.path):
            return format_html('<img src="{}" width="50" height="50" style="border-radius:50%;" />', obj.profile_image.url)
        return format_html('<img src="/media/defaults/user_default.png" width="50" height="50" style="border-radius:50%;" />')
    profile_image_tag.short_description = 'Profile Image'

admin.site.register(User, UserAdmin)



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
        if obj.announcement and obj.announcement.organization and obj.announcement.organization.user:
            return obj.announcement.organization.user.name or obj.announcement.organization.user.email
        return "—"  # fallback if missing
    get_announcement_user.short_description = "Announcement Owner"


    def get_announcement(self, obj):
        return obj.announcement.title
    get_announcement.short_description = "Announcement"

# ----- Organization -----
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "verified", "is_active", "rate", "created_at", "updated_at"
    )
    list_filter = ("verified", "is_active")
    search_fields = ("description", "user__name", "user__email")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {
            "fields": ("user", "description", "website", "location", "rate")
        }),
        ("Status", {
            "fields": ("verified", "is_active")
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
    list_display = ("id", "user", "title", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__name", "title", "message")
    readonly_fields = ("created_at", "updated_at")

# ----- Review -----
# Review admin removed - dependent on Application model which was removed
    
# ----- HelpSupport -----
@admin.register(HelpSupport)
class HelpSupportAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user", "type", "status", 
        "created_at", "title"
    )
    list_filter = ("type", "status", "created_at")
    search_fields = ("user__name", "description")
    readonly_fields = ("created_at",)

    fieldsets = (
        ("User Info", {
            "fields": ("user", "type", "description")
        }),
        ("Status & Response", {
            "fields": ("status", "reply")
        }),
        ("Metadata", {
            "fields": ("created_at",)
        }),
    )