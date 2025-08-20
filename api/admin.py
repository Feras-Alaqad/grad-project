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
    readonly_fields = ("created_at", "updated_at", "last_login", "date_joined")

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
    list_display = ("id", "user", "announcement", "created_at", "updated_at")
    search_fields = ("user__name", "announcement__title")
    readonly_fields = ("created_at", "updated_at")

# ----- Organization -----
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "verified", "is_active", "rate", "created_at", "updated_at")
    list_filter = ("verified", "is_active")
    search_fields = ("description",)
    readonly_fields = ("created_at", "updated_at")

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
    list_display = ("id", "user", "type", "created_at")
    list_filter = ("type",)
    search_fields = ("user__name", "description")
    readonly_fields = ("created_at",)
