from django.contrib import admin
from .models import User, Announcement, Application, UserFavorite, AnnouncementView, Organization, OrganizationDocument, Notification, Review, HelpSupport

# نموذج المستخدم
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "role", "is_active", "date_joined")
    readonly_fields = ("date_joined",)
    search_fields = ("name", "email")
    list_filter = ("role", "is_active")

# نموذج الإعلانات
@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "category", "status", "author", "publish_date", "expiry_date", "created_at")
    readonly_fields = ("created_at", "updated_at", "views_count")
    search_fields = ("title", "description")
    list_filter = ("category", "status", "is_pinned")
    date_hierarchy = "created_at"

# نموذج الطلبات
@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "announcement", "status", "created_at")
    readonly_fields = ("created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("user__name", "announcement__title")

# نموذج المفضلة
@admin.register(UserFavorite)
class UserFavoriteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "announcement", "created_at")
    readonly_fields = ("created_at",)
    search_fields = ("user__name", "announcement__title")

# نموذج مشاهدة الإعلانات
@admin.register(AnnouncementView)
class AnnouncementViewAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "announcement", "ip_address", "viewed_at")
    readonly_fields = ("viewed_at",)
    search_fields = ("user__name", "announcement__title", "ip_address")

# نموذج المؤسسات
@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "user", "rate", "verified", "is_active", "created_at")
    readonly_fields = ("created_at", "updated_at")
    search_fields = ("name", "user__name")
    list_filter = ("verified", "is_active")

# نموذج الوثائق
@admin.register(OrganizationDocument)
class OrganizationDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "organization",)
    search_fields = ("organization__name",)

# نموذج الإشعارات
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "message", "read_status", "created_at")
    readonly_fields = ("created_at",)
    search_fields = ("user__name", "message")
    list_filter = ("read_status",)

# نموذج التقييمات
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "application", "rating")
    search_fields = ("application__user__name", "comment")
    list_filter = ("rating",)

# نموذج الدعم والمساعدة
@admin.register(HelpSupport)
class HelpSupportAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "type", "created_at")
    readonly_fields = ("created_at",)
    search_fields = ("user__name", "description")
    list_filter = ("type",)

