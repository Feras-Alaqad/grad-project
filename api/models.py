from django.db import models

# Create your models here.

from django.contrib.auth.models import AbstractUser, BaseUserManager

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone
from django.core.exceptions import ValidationError

class UserManager(BaseUserManager):
    """
    مدير مخصص للمستخدمين - يستخدم البريد الإلكتروني بدلاً من اسم المستخدم
    """
    def create_user(self, email, password=None, **extra_fields):
        """إنشاء مستخدم عادي"""
        if not email:
            raise ValueError('يجب تعيين حقل البريد الإلكتروني')
        email = self.normalize_email(email)
        if not extra_fields.get('username'):
            username = email.split('@')[0]
            extra_fields['username'] = username
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """إنشاء مستخدم متقدم (مدير)"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True or extra_fields.get('is_superuser') is not True:
            raise ValueError('المستخدم المتقدم يجب أن يحتوي على is_staff=True و is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    نموذج المستخدم المخصص
    - يستخدم البريد الإلكتروني بدلاً من اسم المستخدم
    - يحتوي على أدوار مختلفة (مؤسسة، مدير، مستخدم)
    """
    class Role(models.TextChoices):
        INSTITUTION = "institution", "مؤسسة"
        ADMIN = "admin", "مدير"  
        USER = "user", "مستخدم"

    # إلغاء اسم المستخدم واستخدام البريد الإلكتروني
    username = None
    name = models.CharField(
        max_length=255, 
        blank=True,
        verbose_name="الاسم",
        help_text="اسم المستخدم الكامل"
    )
    email = models.EmailField(
        unique=True,
        verbose_name="البريد الإلكتروني",
        help_text="البريد الإلكتروني الفريد للمستخدم"
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.USER,
        verbose_name="الدور",
        help_text="دور المستخدم في النظام"
    )
    
    # تحديد البريد الإلكتروني كحقل تسجيل الدخول الرئيسي
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = UserManager()

    def __str__(self):
        return f"{self.name or self.email} ({self.get_role_display()})"

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمون"


class Announcement(models.Model):
    """
    نموذج الإعلانات الرئيسي
    - يحتوي على جميع المعلومات الأساسية للإعلان
    - يدعم الحالات المختلفة والفئات المتنوعة
    - يرتبط بالمؤلف ويتتبع المشاهدات
    """
    class Status(models.TextChoices):
        DRAFT = "draft", "مسودة"
        PUBLISHED = "published", "منشور"
        ARCHIVED = "archived", "مؤرشف"

    class Category(models.TextChoices):
        FOOD = "food", "غذائية"
        MEDICAL = "medical", "طبية"
        HEALTH = "health", "صحية"
        EDUCATION = "education", "تعليمية"
        TECHNOLOGY = "technology", "تقنية"
        SPORTS = "sports", "رياضية"
        CULTURAL = "cultural", "ثقافية"
        GENERAL = "general", "عامة"

    # الحقول الأساسية
    title = models.CharField(
        max_length=255,
        verbose_name="العنوان",
        help_text="عنوان الإعلان"
    )
    description = models.TextField(
        verbose_name="الوصف",
        help_text="وصف تفصيلي للإعلان"
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.GENERAL,
        verbose_name="الفئة",
        help_text="فئة الإعلان"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="الحالة",
        help_text="حالة الإعلان الحالية"
    )
    
    # العلاقات
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_announcements',
        verbose_name="المؤلف",
        help_text="المستخدم الذي أنشأ الإعلان"
    )
    organization = models.ForeignKey(
        'Organization',  # استخدام string للإشارة إلى النموذج المعرف لاحقاً
        on_delete=models.CASCADE,
        related_name='announcements',
        null=True,
        blank=True,
        verbose_name="المؤسسة",
        help_text="المؤسسة التي ينتمي إليها الإعلان (اختياري)"
    )
    
    # الحقول الإضافية
    is_pinned = models.BooleanField(
        default=False,
        verbose_name="مثبت",
        help_text="هل الإعلان مثبت في الأعلى؟"
    )
    publish_date = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="تاريخ النشر",
        help_text="تاريخ نشر الإعلان (اختياري)"
    )
    expiry_date = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="تاريخ الانتهاء",
        help_text="تاريخ انتهاء صلاحية الإعلان (اختياري)"
    )
    attachment = models.FileField(
        upload_to='announcements/',
        blank=True,
        verbose_name="المرفق",
        help_text="ملف مرفق مع الإعلان (اختياري)"
    )
    views_count = models.PositiveIntegerField(
        default=0,
        verbose_name="عدد المشاهدات",
        help_text="عدد مرات مشاهدة الإعلان"
    )
    
    # الطوابع الزمنية التلقائية
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاريخ التحديث"
    )

    def __str__(self):
        return self.title

    def clean(self):
        """التحقق من صحة البيانات"""
        if self.expiry_date and self.publish_date:
            if self.expiry_date <= self.publish_date:
                raise ValidationError('تاريخ الانتهاء يجب أن يكون بعد تاريخ النشر')
    
    def is_expired(self):
        """التحقق من انتهاء صلاحية الإعلان"""
        if self.expiry_date:
            return timezone.now() > self.expiry_date
        return False
    
    def is_published(self):
        """التحقق من نشر الإعلان"""
        return self.status == self.Status.PUBLISHED

    class Meta:
        verbose_name = "إعلان"
        verbose_name_plural = "الإعلانات"
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['status', 'category']),
            models.Index(fields=['publish_date']),
            models.Index(fields=['is_pinned', '-created_at']),
        ]


class Application(models.Model):
    """
    نموذج طلبات التقديم على الإعلانات
    - يربط بين المستخدم والإعلان
    - يتتبع حالة الطلب والملاحظات الإدارية
    - يمنع التقديم المتكرر من نفس المستخدم على نفس الإعلان
    """
    class Status(models.TextChoices):
        PENDING = "pending", "قيد الانتظار"
        APPROVED = "approved", "موافق عليه"
        REJECTED = "rejected", "مرفوض"
        IN_REVIEW = "in_review", "قيد المراجعة"
        WITHDRAWN = "withdrawn", "منسحب"

    # العلاقات الأساسية
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name="الإعلان",
        help_text="الإعلان المتقدم عليه"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name="المستخدم",
        help_text="المستخدم المتقدم"
    )
    
    # حالة الطلب والملاحظات
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="الحالة",
        help_text="حالة طلب التقديم"
    )
    admin_notes = models.TextField(
        blank=True,
        verbose_name="ملاحظات إدارية",
        help_text="ملاحظات من الإدارة حول الطلب"
    )
    rejection_reason = models.TextField(
        blank=True,
        verbose_name="سبب الرفض",
        help_text="سبب رفض الطلب (في حالة الرفض)"
    )
    
    # الطوابع الزمنية
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ التقديم"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاريخ التحديث"
    )

    def __str__(self):
        return f"{self.user.name or self.user.email} - {self.announcement.title} - {self.get_status_display()}"

    class Meta:
        verbose_name = "طلب تقديم"
        verbose_name_plural = "طلبات التقديم"
        # منع التقديم المتكرر من نفس المستخدم على نفس الإعلان
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
    نموذج المفضلة للمستخدمين
    - يسمح للمستخدمين بإضافة إعلانات إلى المفضلة
    - علاقة many-to-many بين المستخدمين والإعلانات
    - يمنع إضافة نفس الإعلان للمفضلة أكثر من مرة
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name="المستخدم",
        help_text="المستخدم الذي أضاف الإعلان للمفضلة"
    )
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name="الإعلان",
        help_text="الإعلان المضاف للمفضلة"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإضافة",
        help_text="تاريخ إضافة الإعلان للمفضلة"
    )

    def __str__(self):
        return f"{self.user.name or self.user.email} - {self.announcement.title}"

    class Meta:
        verbose_name = "مفضلة"
        verbose_name_plural = "المفضلات"
        # منع إضافة نفس الإعلان للمفضلة أكثر من مرة من نفس المستخدم
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


class AnnouncementView(models.Model):
    """
    نموذج تتبع مشاهدات الإعلانات
    - يتتبع من شاهد الإعلان ومتى
    - يساعد في إحصائيات المشاهدة الدقيقة
    - يمنع احتساب المشاهدة المتكررة من نفس المستخدم
    """
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name='detailed_views',
        verbose_name="الإعلان"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,  # للسماح بالمشاهدة للمستخدمين غير المسجلين
        blank=True,
        related_name='viewed_announcements',
        verbose_name="المستخدم"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="عنوان IP",
        help_text="عنوان IP للمشاهد (للمستخدمين غير المسجلين)"
    )
    viewed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ المشاهدة"
    )

    def __str__(self):
        viewer = self.user.name if self.user else f"IP: {self.ip_address}"
        return f"{viewer} شاهد {self.announcement.title}"

    class Meta:
        verbose_name = "مشاهدة إعلان"
        verbose_name_plural = "مشاهدات الإعلانات"
        ordering = ['-viewed_at']
        indexes = [
            models.Index(fields=['announcement', '-viewed_at']),
            models.Index(fields=['user', '-viewed_at']),
        ]


class Organization(models.Model):
    """
    نموذج المؤسسات/المنظمات
    - يحتوي على معلومات المؤسسات المختلفة
    - يرتبط بالمستخدمين والإعلانات
    - يتضمن معلومات التحقق والتقييم
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='organizations',
        verbose_name="المستخدم المسؤول",
        help_text="المستخدم المسؤول عن المؤسسة"
    )
    name = models.CharField(
        max_length=255,
        verbose_name="اسم المؤسسة",
        help_text="الاسم الرسمي للمؤسسة"
    )
    description = models.TextField(
        blank=True,
        verbose_name="وصف المؤسسة",
        help_text="وصف تفصيلي عن المؤسسة وأنشطتها"
    )
    website = models.URLField(
        blank=True,
        verbose_name="الموقع الإلكتروني",
        help_text="رابط الموقع الرسمي للمؤسسة"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="رقم الهاتف",
        help_text="رقم الهاتف الرسمي للمؤسسة"
    )
    email = models.EmailField(
        blank=True,
        verbose_name="البريد الإلكتروني",
        help_text="البريد الإلكتروني الرسمي للمؤسسة"
    )
    location = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="الموقع",
        help_text="العنوان أو الموقع الجغرافي للمؤسسة"
    )
    rate = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        verbose_name="التقييم",
        help_text="تقييم المؤسسة من 0.00 إلى 5.00"
    )
    verified = models.BooleanField(
        default=False,
        verbose_name="محقق",
        help_text="هل المؤسسة محققة من قبل الإدارة؟"
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="نشطة",
        help_text="هل المؤسسة نشطة حالياً؟"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ التسجيل"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="تاريخ التحديث"
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "مؤسسة"
        verbose_name_plural = "المؤسسات"
        ordering = ['-rate', '-created_at']
        indexes = [
            models.Index(fields=['verified', 'is_active']),
            models.Index(fields=['-rate']),
        ]


class OrganizationDocument(models.Model):
    """
    نموذج وثائق المؤسسات
    - يحتوي على جميع الوثائق المطلوبة للتحقق من المؤسسة
    - يدعم أنواع مختلفة من الوثائق
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name="المؤسسة"
    )
    registration_docs = models.FileField(
        upload_to='organizations/registration/',
        blank=True,
        verbose_name="وثائق التسجيل",
        help_text="وثائق تسجيل المؤسسة الرسمية"
    )
    financial_report = models.FileField(
        upload_to='organizations/financial/',
        blank=True,
        verbose_name="التقرير المالي",
        help_text="التقارير المالية للمؤسسة"
    )
    activity_proof = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="دليل النشاط",
        help_text="بيانات JSON تحتوي على أدلة أنشطة المؤسسة"
    )

    def __str__(self):
        return f"وثائق {self.organization.name}"

    class Meta:
        verbose_name = "وثيقة مؤسسة"
        verbose_name_plural = "وثائق المؤسسات"


class Notification(models.Model):
    """
    نموذج الإشعارات
    - يرسل إشعارات للمستخدمين حول أحداث مختلفة
    - يدعم حالات قراءة/عدم قراءة الإشعارات
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="المستخدم",
        help_text="المستخدم المرسل إليه الإشعار"
    )
    message = models.TextField(
        verbose_name="رسالة الإشعار",
        help_text="نص الإشعار المرسل للمستخدم"
    )
    read_status = models.BooleanField(
        default=False,
        verbose_name="حالة القراءة",
        help_text="هل تم قراءة الإشعار؟"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإرسال"
    )

    def __str__(self):
        status = "مقروء" if self.read_status else "غير مقروء"
        return f"إشعار لـ {self.user.name or self.user.email} - {status}"

    def mark_as_read(self):
        """تحديد الإشعار كمقروء"""
        self.read_status = True
        self.save()

    class Meta:
        verbose_name = "إشعار"
        verbose_name_plural = "الإشعارات"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'read_status']),
            models.Index(fields=['-created_at']),
        ]


class Review(models.Model):
    """
    نموذج التقييمات والمراجعات
    - يسمح للمستخدمين بتقييم طلبات التقديم
    - يحتوي على تعليقات وتقييم رقمي
    """
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name="طلب التقديم",
        help_text="طلب التقديم المراد تقييمه"
    )
    comment = models.TextField(
        blank=True,
        verbose_name="التعليق",
        help_text="تعليق أو ملاحظات حول الطلب"
    )
    rating = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="التقييم",
        help_text="التقييم من 1 إلى 5"
    )

    def __str__(self):
        return f"تقييم طلب {self.application.user.name} - {self.rating}/5"

    def clean(self):
        """التحقق من صحة التقييم"""
        if self.rating < 1 or self.rating > 5:
            raise ValidationError('التقييم يجب أن يكون بين 1 و 5')

    class Meta:
        verbose_name = "تقييم"
        verbose_name_plural = "التقييمات"
        # منع تقييم نفس الطلب أكثر من مرة من نفس المراجع
        constraints = [
            models.UniqueConstraint(
                fields=['application'], 
                name='unique_application_review'
            )
        ]


class HelpSupport(models.Model):
    """
    نموذج الدعم والمساعدة
    - يسمح للمستخدمين بإرسال طلبات دعم
    - يدعم أنواع مختلفة من طلبات الدعم
    """
    class SupportType(models.TextChoices):
        TECHNICAL = "technical", "مشكلة تقنية"
        ACCOUNT = "account", "مشكلة في الحساب"
        GENERAL = "general", "استفسار عام"
        COMPLAINT = "complaint", "شكوى"
        SUGGESTION = "suggestion", "اقتراح"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='support_requests',
        verbose_name="المستخدم",
        help_text="المستخدم الذي أرسل طلب الدعم"
    )
    description = models.TextField(
        verbose_name="وصف المشكلة",
        help_text="وصف تفصيلي للمشكلة أو الاستفسار"
    )
    type = models.CharField(
        max_length=20,
        choices=SupportType.choices,
        default=SupportType.GENERAL,
        verbose_name="نوع الطلب",
        help_text="نوع طلب الدعم"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإرسال"
    )

    def __str__(self):
        return f"طلب دعم من {self.user.name or self.user.email} - {self.get_type_display()}"

    class Meta:
        verbose_name = "طلب دعم"
        verbose_name_plural = "طلبات الدعم"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['type', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]