from django.contrib import admin
from .models import (
    User, Announcement, AnnouncementCategory, Application,
    UserFavorite, Organization, OrganizationDocument,
    Notification, Review, HelpSupport
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
    list_display = ("id", "title", "organization", "start_date", "end_date", "created_at", "updated_at")
    list_filter = ("organization",)
    search_fields = ("title", "description")
    readonly_fields = ("created_at", "updated_at")

# ----- AnnouncementCategory -----
@admin.register(AnnouncementCategory)
class AnnouncementCategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)

# ----- Application -----
@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "announcement", "user", "status", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("user__name", "announcement__title")
    readonly_fields = ("created_at", "updated_at")

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
    search_fields = ("user__name", "application__announcement__title", "application__user__name")
    readonly_fields = ("created_at", "updated_at")

    def get_announcement_user(self, obj):
        # صاحب الإعلان
        return obj.application.user.name or obj.application.user.email
    get_announcement_user.short_description = "Announcement Owner"

    def get_announcement(self, obj):
        return obj.application.announcement.title
    get_announcement.short_description = "Announcement"

    def get_announcement(self, obj):
        return obj.application.announcement.title
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
    list_display = ("id", "user", "title", "read_status", "created_at")
    list_filter = ("read_status",)
    search_fields = ("user__name", "title", "message")
    readonly_fields = ("created_at",)

# ----- Review -----
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "rating")
    search_fields = ("application__user__name",)
    
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