from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.contrib.auth.tokens import default_token_generator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


from .models import (
    User, Announcement, AnnouncementCategory, Application,
    UserFavorite, Organization, OrganizationDocument,
    Notification, Review, HelpSupport
)
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        if user.role == User.Role.ORGANIZATION:
            org = Organization.objects.filter(user=user).first()
            if not org:
                raise serializers.ValidationError({"detail": "Organization profile not found."})
            
            if org.is_rejected:
                raise serializers.ValidationError({
                    "detail": f"Your organization registration has been rejected: {org.rejection_reason}"
                })
            
            if not org.is_active:
                raise serializers.ValidationError({
                    "detail": "Your organization account is not active yet. Please wait for admin approval."
                })

        return data


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

    class Meta:
        model = User
        fields = ('email', 'name', 'phone', 'password', 'password_confirm')  # بدون role

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
            role=User.Role.USER 
        )
    
class OrganizationSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})

    description = serializers.CharField(required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)
    location = serializers.CharField(required=False, allow_blank=True)
    rate = serializers.IntegerField(required=False, min_value=1, max_value=5)

    class Meta:
        model = User
        fields = (
            'email', 'name', 'phone', 'password', 'password_confirm',
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

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('password_confirm', None)

        # بيانات المؤسسة فقط
        org_data = {
            'description': validated_data.pop('description', ''),
            'website': validated_data.pop('website', ''),
            'location': validated_data.pop('location', ''),
            'rate': validated_data.pop('rate', 1),
            'verified': False,
            'is_active': False,
        }

        # إنشاء المستخدم مع role ORGANIZATION
        user = User.objects.create_user(
            email=validated_data['email'],
            password=password,
            name=validated_data.get('name', ''),
            phone=validated_data.get('phone', ''),
            role=User.Role.ORGANIZATION
        )

        # إنشاء المنظمة وربطها بالمستخدم
        Organization.objects.create(
            user=user,
            **org_data
        )

        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "role",
            "is_active",
            "created_at",
            "updated_at"
        ]
        read_only_fields = ('id', 'created_at', 'updated_at')
        extra_kwargs = {
            'email': {'required': True, 'allow_blank': False},
            'name': {'required': True, 'allow_blank': False},
            'phone': {'required': False, 'allow_blank': True},
            'role': {'required': True, 'allow_blank': False}
        }


# serializer.py
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
    # هنا نخلي الحقول تبع اليوزر قابلة للقراءة والكتابة بنفس الوقت
    name = serializers.CharField(source='user.name', required=False)
    email = serializers.EmailField(source='user.email', required=False)
    phone = serializers.CharField(source='user.phone', required=False)

    class Meta:
        model = Organization
        fields = [
            'name', 'email', 'phone',
            'description', 'website',
            'location', 'rate', 'verified', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['rate', 'verified', 'is_active', 'created_at', 'updated_at']

    def update(self, instance, validated_data):
        # تحديث بيانات اليوزر المرتبطة
        user_data = validated_data.pop('user', {})
        user = instance.user
        for attr, value in user_data.items():
            setattr(user, attr, value)
        user.save()

        # تحديث بيانات الـ Organization
        return super().update(instance, validated_data)

class UserFavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserFavorite
        fields = ['id', 'user', 'announcement', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

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
    """Serializer for listing announcements (public view)"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    organization_name = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'description', 'start_date', 'end_date',
            'url', 'category_name', 'organization_name', 'creator_name',
            'status', 'created_at', 'updated_at'
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


class AnnouncementDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed announcement view"""
    category = AnnouncementCategorySerializer(read_only=True)
    organization_name = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()
    applications_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'description', 'start_date', 'end_date',
            'url', 'category', 'organization_name', 'creator_name',
            'applications_count', 'status', 'created_at', 'updated_at'
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

    def get_applications_count(self, obj):
        return obj.applications.count()


class AnnouncementCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating announcements"""
    organization_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    organization_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    # Response fields
    creator_name = serializers.SerializerMethodField()
    organization_display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'description', 'start_date', 'end_date',
            'url', 'category', 'organization_id', 'organization_name', 'status', 'created_at',
            'creator_name', 'organization_display_name'
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
    
    class Meta:
        model = Announcement
        fields = [
            'title', 'description', 'start_date', 'end_date',
            'url', 'category'
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
    
    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'description', 'start_date', 'end_date',
            'url', 'category_name', 'organization_name', 'creator_name',
            'status', 'admin_notes', 'created_at', 'updated_at'
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


class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


class OrganizationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationDocument
        fields = "__all__"
        read_only_fields = ("created_at",)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = "__all__"
        read_only_fields = ("created_at",)


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = "__all__"


class HelpSupportSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpSupport
        fields = "__all__"
        read_only_fields = ("created_at",)
