from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
import os



from .models import (
    User, Announcement, AnnouncementCategory,
    UserFavorite, Organization, OrganizationDocument,
    Notification, HelpSupport, UserApplicationTracking
)

# =========================
# 🔹 Utility Functions
# =========================

def get_safe_profile_image_url_serializer(request, user):
    """
    Safely get profile image URL for serializers, fallback to default if file doesn't exist
    """
    if user.profile_image:
        # Check if the file actually exists
        file_path = os.path.join(settings.MEDIA_ROOT, str(user.profile_image))
        if os.path.exists(file_path):
            if request:
                return request.build_absolute_uri(user.profile_image.url)
            else:
                return f"{settings.BASE_URL}{user.profile_image.url}"
        else:
            # File doesn't exist, use default
            default_image_path = 'defaults/user_default.png'
            if request:
                return request.build_absolute_uri(settings.MEDIA_URL + default_image_path)
            else:
                return f"{settings.BASE_URL}{settings.MEDIA_URL}{default_image_path}"
    else:
        # No profile image set, use default
        default_image_path = 'defaults/user_default.png'
        if request:
            return request.build_absolute_uri(settings.MEDIA_URL + default_image_path)
        else:
            return f"{settings.BASE_URL}{settings.MEDIA_URL}{default_image_path}"

def get_safe_announcement_image_url_serializer(request, announcement):
    """
    Safely get announcement image URL for serializers, fallback to default if file doesn't exist
    """
    if announcement.image:
        # Check if the file actually exists
        file_path = os.path.join(settings.MEDIA_ROOT, str(announcement.image))
        if os.path.exists(file_path):
            if request:
                return request.build_absolute_uri(announcement.image.url)
            else:
                return f"{settings.BASE_URL}{announcement.image.url}"
        else:
            # File doesn't exist, use default
            default_image_path = 'defaults/announcement_default.png'
            if request:
                return request.build_absolute_uri(settings.MEDIA_URL + default_image_path)
            else:
                return f"{settings.BASE_URL}{settings.MEDIA_URL}{default_image_path}"
    else:
        # No image set, use default
        default_image_path = 'defaults/announcement_default.png'
        if request:
            return request.build_absolute_uri(settings.MEDIA_URL + default_image_path)
        else:
            return f"{settings.BASE_URL}{settings.MEDIA_URL}{default_image_path}"

def get_safe_organization_profile_image_url_serializer(request, organization):
    """
    Safely get organization profile image URL for serializers, fallback to default if file doesn't exist
    """
    default_image_path = 'defaults/organization_default.png'
    if getattr(organization, 'profile_image', None):
        file_path = os.path.join(settings.MEDIA_ROOT, str(organization.profile_image))
        if os.path.exists(file_path):
            if request:
                return request.build_absolute_uri(organization.profile_image.url)
            else:
                return f"{settings.BASE_URL}{organization.profile_image.url}"
        # File missing → use default
    if request:
        return request.build_absolute_uri(settings.MEDIA_URL + default_image_path)
    else:
        return f"{settings.BASE_URL}{settings.MEDIA_URL}{default_image_path}"
# =========================
# 🔹 User Serializers
# =========================
class BaseSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, min_length=8, style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True, style={'input_type': 'password'}
    )
    profile_image = serializers.ImageField(
        required=False,
        allow_null=True
    )

    class Meta:
        model = User
        fields = ('email', 'name', 'phone', 'profile_image', 'password', 'password_confirm') 

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use")
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match"}
            )
        return attrs


class UserSignupSerializer(BaseSignupSerializer):
    def create(self, validated_data):
        validated_data.pop('password_confirm', None)
        return User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            phone=validated_data.get('phone', ''),
            name=validated_data.get('name', ''),
            profile_image=validated_data.get('profile_image', None),
            role=User.Role.USER
        )

    
class OrganizationSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})
    description = serializers.CharField()   
    website = serializers.URLField()        
    location = serializers.CharField()      
    rate = serializers.IntegerField(default=1 ,min_value=1, max_value=5)  
    profile_image = serializers.ImageField(required=False, allow_null=True)
    phone = serializers.CharField(required=True, allow_blank=False)

    class Meta:
        model = User
        fields = (
            'email', 'name', 'phone', 'profile_image', 'password', 'password_confirm',
            'description', 'website', 'location', 'rate'
        )


    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match"})
        return attrs

    def validate_phone(self, value):
        if not value:
            raise serializers.ValidationError("Phone number is required.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('password_confirm', None)

        # Extract optional org fields
        description = validated_data.pop('description', '')
        website = validated_data.pop('website', '')
        location = validated_data.pop('location', '')
        rate = validated_data.pop('rate', 1)
        org_profile_image = validated_data.pop('profile_image', None)

        # Build org data, preserving default image when none provided
        org_data = {
            'description': description,
            'website': website,
            'location': location,
            'rate': rate,
            'verified': False,
            'is_active': True,
        }
        if org_profile_image is not None:
            org_data['profile_image'] = org_profile_image

        user = User.objects.create_user(
            email=validated_data['email'],
            password=password,
            name=validated_data.get('name', ''),
            phone=validated_data.get('phone', ''),
            role=User.Role.ORGANIZATION
        )

        Organization.objects.create(
            user=user,
            **org_data
        )

        return user

class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

    def validate(self, attrs):
        self.token = attrs['refresh']
        return attrs

    def save(self, **kwargs):
        try:
            token = RefreshToken(self.token)
            token.blacklist()  # وضع الـ token في blacklist
        except Exception as e:
            raise serializers.ValidationError("Token is invalid or expired")

class UserSerializer(serializers.ModelSerializer):
    profile_image = serializers.ImageField(required=False, allow_null=True)  

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "role",
            "profile_image",  
            "is_active",
            "created_at",
            "updated_at"
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')  
        extra_kwargs = {
            'email': {'required': True, 'allow_blank': False},
            'name': {'required': True, 'allow_blank': False},
            'phone': {'required': False, 'allow_blank': True},
        }
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request', None)
        # Use safe profile image URL to handle missing files
        data['profile_image'] = get_safe_profile_image_url_serializer(request, instance)
        return data


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
            self.context['user'] = user  # نخزن المستخدم في السياق
        except User.DoesNotExist:
            raise serializers.ValidationError("This email is not registered")
        return value


class ResetPasswordSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        try:
            user = User.objects.get(pk=attrs['user_id'])

            # check token validity
            if not default_token_generator.check_token(user, attrs['token']):
                raise serializers.ValidationError({"token": "Invalid or expired reset token"})

            # check password match
            if attrs['password'] != attrs['password_confirm']:
                raise serializers.ValidationError({"password_confirm": "Passwords do not match"})

            # validate password strength
            validate_password(attrs['password'], user)

            # pass user to serializer context
            self.context['user'] = user

        except User.DoesNotExist:
            raise serializers.ValidationError({"user_id": "Invalid user ID"})

        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    new_password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    new_password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect")
        return value

    def validate_new_password(self, value):
        try:
            validate_password(value, self.context['request'].user)
        except ValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password_confirm": "New passwords do not match"})
        return attrs
    
class OrganizationProfileSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.name', required=True)
    email = serializers.EmailField(source='user.email', required=True)
    phone = serializers.CharField(source='user.phone', required=True)
    role = serializers.CharField(source='user.role', required=False)
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            'id','name', 'email', 'phone', 'profile_image', 'role',
            'description', 'website', 'location', 'rate', 'verified', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['rate', 'verified', 'is_active', 'created_at', 'updated_at']

    def get_profile_image(self, obj):
        request = self.context.get('request', None)
        return get_safe_organization_profile_image_url_serializer(request, obj)

    def update(self, instance, validated_data):
        # تحديث بيانات اليوزر المرتبطة
        user_data = validated_data.pop('user', {})
        user = instance.user
        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()

        # تحديث بيانات الـ Organization
        return super().update(instance, validated_data)



class AnnouncementDetailSerializer(serializers.ModelSerializer):
    """Serializer for announcement details in favorites"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    organization_name = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    
    def get_creator_name(self, obj):
        """Return creator name or 'Admin' if created by admin"""
        if obj.created_by and obj.created_by.role == User.Role.ADMIN:
            return "Admin"
        elif obj.created_by:
            return obj.created_by.name
        return "Unknown"
    
    def get_organization_name(self, obj):
        """Return organization name or None if no organization"""
        if obj.organization_name:
            return obj.organization_name
        elif obj.organization:
            return obj.organization.user.name
        return None
    
    def get_image(self, obj):
        """Return full URL for announcement image"""
        request = self.context.get('request')
        return get_safe_announcement_image_url_serializer(request, obj)
    
    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'description', 'start_date', 'end_date',
            'url', 'category_name', 'organization_name', 'creator_name',
            'status', 'created_at', 'updated_at', 'image'
        ]

class UserFavoriteSerializer(serializers.ModelSerializer):
    announcement = AnnouncementDetailSerializer(read_only=True)
    
    class Meta:
        model = UserFavorite
        fields = ['id', 'announcement', 'created_at', 'updated_at']
        read_only_fields = ['id', 'announcement', 'created_at', 'updated_at']

class OrganizationToggleActiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['is_active', 'block_reason']

    def update(self, instance, validated_data):
        # Toggle logic
        if instance.is_active:  
            # كان True → يصير False
            instance.is_active = False
            instance.block_reason = validated_data.get('block_reason', '')

            # إبطال التوكنات
            tokens = OutstandingToken.objects.filter(user=instance.user)
            for token in tokens:
                BlacklistedToken.objects.get_or_create(token=token)

        else:  
            # كان False → يصير True
            instance.is_active = True
            # نتجاهل block_reason حتى لو مبعوث
            instance.block_reason = ""

        instance.save()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_active:
            # ما نعرض السبب لو المؤسسة مفعلة
            data.pop('block_reason', None)
        return data


# =========================
# 🔹 Models Serializers
# =========================

# =========================
# 🔹 Announcement Serializers
# =========================

class AnnouncementCategorySerializer(serializers.ModelSerializer):
    announcements_count = serializers.SerializerMethodField()
    
    class Meta:
        model = AnnouncementCategory
        fields = ['id', 'name', 'announcements_count']
    
    def get_announcements_count(self, obj):
        return obj.announcements.filter(status=Announcement.Status.APPROVED).count()


class AnnouncementListSerializer(serializers.ModelSerializer):
    """Improved serializer for listing announcements with conditional admin fields"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    organization_name = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()
    admin_notes = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'description', 'start_date', 'end_date',
            'url', 'category_name', 'organization_name', 'creator_name',
            'status', 'admin_notes', 'created_at', 'updated_at', 'image'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']
    
    def get_creator_name(self, obj):
        """Return creator name or 'Admin' if created by admin"""
        if obj.created_by.role == User.Role.ADMIN:
            return "Admin"
        return obj.created_by.name
    
    def get_organization_name(self, obj):
        """Return organization name or None if no organization"""
        if obj.organization_name:
            return obj.organization_name
        elif obj.organization:
            return obj.organization.user.name
        return None
    
    def get_admin_notes(self, obj):
        """Return admin_notes for admin and owning organization/creator; empty for others"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return ""

        user = request.user
        # Admins can always see admin_notes
        if user.role == User.Role.ADMIN:
            return obj.admin_notes or ""

        # Organizations can see admin_notes for announcements they own or created
        if user.role == User.Role.ORGANIZATION:
            owns_announcement = False
            try:
                # If announcement is linked to an Organization, compare its user
                if getattr(obj, 'organization', None) and getattr(obj.organization, 'user_id', None):
                    owns_announcement = (obj.organization.user_id == user.id)
            except Exception:
                # Be conservative on any attribute errors
                owns_announcement = False

            # Also allow if the current user is the creator of the announcement
            if owns_announcement or (getattr(obj, 'created_by_id', None) == user.id):
                return obj.admin_notes or ""

        # Regular users or other organizations should not see admin notes
        return ""
    
    def get_image(self, obj):
        """Return full URL for announcement image"""
        request = self.context.get('request')
        return get_safe_announcement_image_url_serializer(request, obj)


class AnnouncementDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed announcement view"""
    category = AnnouncementCategorySerializer(read_only=True)
    organization_name = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'description', 'start_date', 'end_date',
            'url', 'category', 'organization_name', 'creator_name',
            'status', 'created_at', 'updated_at', 'image'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']
    
    def get_creator_name(self, obj):
        """Return creator name or 'Admin' if created by admin"""
        if obj.created_by.role == User.Role.ADMIN:
            return "Admin"
        return obj.created_by.name
    
    def get_organization_name(self, obj):
        """Return organization name or None if no organization"""
        if obj.organization_name:
            return obj.organization_name
        elif obj.organization:
            return obj.organization.user.name
        return None
    
    def get_image(self, obj):
        """Return full URL for announcement image"""
        request = self.context.get('request')
        return get_safe_announcement_image_url_serializer(request, obj)

    # Applications count removed - no longer applicable


class AnnouncementCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating announcements"""
    organization_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    organization_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    image = serializers.ImageField(required=False, allow_null=True)
    
    # Response fields
    creator_name = serializers.SerializerMethodField()
    organization_display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'description', 'start_date', 'end_date',
            'url', 'category', 'organization_id', 'organization_name', 'status', 'created_at',
            'creator_name', 'organization_display_name', 'image'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'creator_name', 'organization_display_name']
    
    def get_creator_name(self, obj):
        """Return creator name or 'Admin' if created by admin"""
        if obj.created_by.role == User.Role.ADMIN:
            return "Admin"
        return obj.created_by.name
    
    def get_organization_display_name(self, obj):
        """Return organization name or None if no organization"""
        if obj.organization_name:
            return obj.organization_name
        elif obj.organization:
            return obj.organization.user.name
        return None
    
    def validate(self, attrs):
        user = self.context['request'].user
        organization_id = attrs.get('organization_id')
        organization_name = attrs.get('organization_name')
        
        # Handle organization field based on user role
        if user.role == User.Role.ORGANIZATION:
            # Organization users: automatically set their organization
            try:
                organization = Organization.objects.get(user=user)
                attrs['organization'] = organization
                attrs['organization_name'] = None
            except Organization.DoesNotExist:
                raise serializers.ValidationError("Organization profile not found")
            # Remove organization fields from input if provided
            attrs.pop('organization_id', None)
            attrs.pop('organization_name', None)
        
        elif user.role == User.Role.ADMIN:
            # Admin users: can select existing organization or specify custom name
            if organization_id and organization_name:
                raise serializers.ValidationError({
                    'organization': 'Cannot specify both organization_id and organization_name. Choose one.'
                })
            
            if organization_id:
                # Link to existing organization
                try:
                    organization = Organization.objects.get(id=organization_id)
                    attrs['organization'] = organization
                    attrs['organization_name'] = None
                except Organization.DoesNotExist:
                    raise serializers.ValidationError({
                        'organization_id': 'Organization with this ID does not exist.'
                    })
            elif organization_name:
                # Use custom organization name
                attrs['organization_name'] = organization_name.strip()
                attrs['organization'] = None
            else:
                # No organization specified
                attrs['organization_name'] = None
                attrs['organization'] = None
            
            # Remove organization_id from attrs as it's not a model field
            attrs.pop('organization_id', None)
        
        # Validate dates
        if attrs.get('start_date') and attrs.get('end_date'):
            if attrs['end_date'] <= attrs['start_date']:
                raise serializers.ValidationError("End date must be after start date")
        
        return attrs
    
    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['created_by'] = user
        
        # Set status based on user role
        if user.role == User.Role.ADMIN:
            validated_data['status'] = Announcement.Status.APPROVED
        else:
            validated_data['status'] = Announcement.Status.PENDING
        
        return super().create(validated_data)


class AnnouncementUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating announcements"""
    title = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    url = serializers.URLField(required=False)
    image = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = Announcement
        fields = [
            'title', 'description', 'start_date', 'end_date',
            'url', 'category', 'image'
        ]
    
    def validate(self, attrs):
        # Validate dates
        instance = self.instance
        start_date = attrs.get('start_date', instance.start_date)
        end_date = attrs.get('end_date', instance.end_date)
        
        if start_date and end_date and end_date <= start_date:
            raise serializers.ValidationError("End date must be after start date")
        
        return attrs
    
    def update(self, instance, validated_data):
        user = self.context['request'].user
        
        # If organization user is updating, set status back to pending for admin approval
        if user.role == User.Role.ORGANIZATION:
            validated_data['status'] = Announcement.Status.PENDING
        # Admin updates remain approved
        elif user.role == User.Role.ADMIN:
            # Admin can keep current status or it will be handled by approval endpoint
            pass
            
        return super().update(instance, validated_data)


class AnnouncementAdminSerializer(serializers.ModelSerializer):
    """Serializer for admin view of announcements"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    organization_name = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()
    image = serializers.ImageField(read_only=True)
    
    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'description', 'start_date', 'end_date',
            'url', 'category_name', 'organization_name', 'creator_name',
            'status', 'admin_notes', 'created_at', 'updated_at', 'image'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
    
    def get_creator_name(self, obj):
        """Return creator name or 'Admin' if created by admin"""
        if obj.created_by.role == User.Role.ADMIN:
            return "Admin"
        return obj.created_by.name
    
    def get_organization_name(self, obj):
        """Return organization name or None if no organization"""
        if obj.organization_name:
            return obj.organization_name
        elif obj.organization:
            return obj.organization.user.name
        return None


class AnnouncementApprovalSerializer(serializers.ModelSerializer):
    """Serializer for admin to approve/reject announcements"""
    
    class Meta:
        model = Announcement
        fields = ['status', 'admin_notes']
    
    def validate_status(self, value):
        if value not in [Announcement.Status.APPROVED, Announcement.Status.REJECTED]:
            raise serializers.ValidationError("Status must be either approved or rejected")
        return value


# Application serializers removed - announcements handle their own status workflow
# Users view approved announcements and apply through external URLs



class OrganizationSerializer(serializers.ModelSerializer):
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")

    def get_profile_image(self, obj):
        request = self.context.get('request', None)
        return get_safe_organization_profile_image_url_serializer(request, obj)


class OrganizationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationDocument
        fields = "__all__"
        read_only_fields = ("created_at",)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")



class OrganizationBasicSerializer(serializers.ModelSerializer):
    """Serializer للمؤسسات - للاستخدام في قائمة الاختيار"""
    user_name = serializers.CharField(source='user.name', read_only=True)
    
    class Meta:
        model = Organization
        fields = ['id', 'user_name', 'verified', 'is_active']



class HelpSupportSerializer(serializers.ModelSerializer):
    """Serializer for support requests"""
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    type = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = HelpSupport
        fields = [
            'id', 'user', 'user_name', 'user_email', 'title', 'description',
            'type', 'type_display',
            'status', 'status_display', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'status', 'status_display']
    
    def validate_type(self, value):
        if value not in [choice[0] for choice in HelpSupport.SupportType.choices]:
            raise serializers.ValidationError("Invalid request type")
        return value
    
    def validate_description(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Issue description must be at least 10 characters long")
        return value.strip()

class HelpSupportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new support requests"""

    title = serializers.CharField(required=True)
    description = serializers.CharField(required=True)
    type = serializers.ChoiceField(
        choices=HelpSupport.SupportType.choices,
        required=True
    )
    status = serializers.CharField(read_only=True, default=HelpSupport.Status.PENDING)

    class Meta:
        model = HelpSupport
        fields = ['title', 'description', 'type', 'status']

    def validate(self, attrs):
        request_type = attrs.get('type')

        # description و title مطلوبان دائمًا
        if not attrs.get('description'):
            raise serializers.ValidationError({'description': 'Description is required.'})
        if not attrs.get('title'):
            raise serializers.ValidationError({'title': 'Title is required.'})

        return attrs

class HelpSupportAdminSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    status = serializers.CharField(read_only=True)  # إضافة حالة الطلب

    class Meta:
        model = HelpSupport
        fields = [
            'id', 'user', 'user_name', 'user_email',
            'title', 'description', 'type_display',
            'status', 'status_display',
            'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'status', 'type']

class OrganizationDocumentSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True) 

    class Meta:
        model = OrganizationDocument
        fields = [
            "id",
            "registration_docs",
            "financial_report",
            "activity_proof",
            "address_proof",
            "status",         
            "created_at"
        ]
        read_only_fields = ["id", "status", "created_at"]

        extra_kwargs = {
            "registration_docs": {"required": True, "allow_null": False},
            "financial_report": {"required": True, "allow_null": False},
            "activity_proof": {"required": True, "allow_null": False},
            "address_proof": {"required": True, "allow_null": False},
        }

    def validate(self, attrs):
        """تأكد أن كل ملف تم رفعه بشكل صحيح"""
        for field in ["registration_docs", "financial_report", "activity_proof", "address_proof"]:
            file = attrs.get(field)
            if not file:
                raise serializers.ValidationError({field: f"{field.replace('_', ' ').title()} is required."})
            if hasattr(file, "size") and file.size == 0:
                raise serializers.ValidationError({field: f"{field.replace('_', ' ').title()} file is empty."})
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user

        # تأكد أن المستخدم هو مؤسسة
        if user.role != user.Role.ORGANIZATION:
            raise serializers.ValidationError("Only organizations can upload documents.")
        
        # الحصول على المؤسسة الخاصة بالمستخدم
        try:
            organization = Organization.objects.get(user=user)
        except Organization.DoesNotExist:
            raise serializers.ValidationError("This user does not have an organization.")

        validated_data["organization"] = organization
        return super().create(validated_data)

    
class OrganizationSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="user.name", read_only=True)
    profile_image = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)

    class Meta:
        model = Organization
        fields = [
            "id",
            "organization_name",
            "profile_image",
            "email",           
            "phone",           
            "description",
            "website",
            "location",
            "rate",
            "verified",
            "is_active",
            "created_at",
            "updated_at"
        ]

    def get_profile_image(self, obj):
        request = self.context.get('request', None)
        return get_safe_organization_profile_image_url_serializer(request, obj)

class OrganizationAdminSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="user.name", read_only=True)
    profile_image = serializers.SerializerMethodField()
    email = serializers.EmailField(source="user.email", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)

    class Meta:
        model = Organization
        fields = [
            "id",
            "organization_name",
            "profile_image",
            "email",           
            "phone",           
            "description",
            "website",
            "location",
            "rate",
            "verified",
            "is_active",
            "block_reason",
            "created_at",
            "updated_at"
        ]

    def get_profile_image(self, obj):
        request = self.context.get('request', None)
        return get_safe_organization_profile_image_url_serializer(request, obj)

class OrganizationVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'verified']
        read_only_fields = ['id']

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['title', 'message']

class NotificationDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'created_at', 'updated_at']

class NotificationToUserSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(write_only=True, help_text="ID of the user to send notification to")

    class Meta:
        model = Notification
        fields = ['title', 'message', 'user_id']

class NotificationListSerializer(serializers.ModelSerializer):
    recipient = serializers.CharField(source='user.name', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'recipient', 'title', 'message', 'created_at']

class UserApplicationTrackingSerializer(serializers.ModelSerializer):
    """Serializer for user application tracking"""
    announcement = AnnouncementDetailSerializer(read_only=True)
    
    class Meta:
        model = UserApplicationTracking
        fields = [
            'id',
            'announcement',
            'status',
            'notes',
            'reminder_date',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class UserApplicationTrackingCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating application tracking entries"""
    
    class Meta:
        model = UserApplicationTracking
        fields = ['notes', 'status', 'reminder_date']
        
    def create(self, validated_data):
        # Get user and announcement from context
        user = self.context['request'].user
        announcement = self.context['announcement']
        
        # Create or update the tracking entry
        tracking, created = UserApplicationTracking.objects.get_or_create(
            user=user,
            announcement=announcement,
            defaults=validated_data
        )
        
        if not created:
            # Update existing entry
            for attr, value in validated_data.items():
                setattr(tracking, attr, value)
            tracking.save()
            
        return tracking
