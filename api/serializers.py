from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth.tokens import default_token_generator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken



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
        read_only_fields = ('id', 'created_at', 'updated_at')  # role محمي من التغيير
        extra_kwargs = {
            'email': {'required': True, 'allow_blank': False},
            'name': {'required': True, 'allow_blank': False},
            'phone': {'required': False, 'allow_blank': True},
        }



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
    application_id = serializers.IntegerField(source="application.id", read_only=True)
    user = serializers.CharField(source="application.user.name", read_only=True)
    announcement = serializers.CharField(source="application.announcement.title", read_only=True)

    class Meta:
        model = UserFavorite
        fields = ['id', 'application_id', 'user', 'announcement', 'created_at', 'updated_at']
        read_only_fields = ['id', 'application_id', 'user', 'announcement', 'created_at', 'updated_at']
    
    def validate_user(self, value):
        if value.user_type != 'user':
            raise serializers.ValidationError("Only users of type 'user' can add favorites.")
        return value

class OrganizationToggleActiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['is_active', 'block_reason']

    def update(self, instance, validated_data):
        is_active = validated_data.get('is_active', instance.is_active)

        if not is_active:  # Blocking the organization
            instance.is_active = False
            instance.block_reason = validated_data.get('block_reason', '')

            # إبطال كل التوكنات الصالحة للمؤسسة
            tokens = OutstandingToken.objects.filter(user=instance.user)
            for token in tokens:
                BlacklistedToken.objects.get_or_create(token=token)

        else:  # Reactivating
            instance.is_active = True

        instance.save()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_active:
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
    target_org_name = serializers.CharField(source='target_org.user.name', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = HelpSupport
        fields = [
            'id', 'user', 'user_name', 'user_email', 'description', 
            'target_org', 'target_org_name', 'priority_display',
            'type_display', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']
    
    def validate_type(self, value):
        """Validate request type"""
        if value not in [choice[0] for choice in HelpSupport.SupportType.choices]:
            raise serializers.ValidationError("Invalid request type")
        return value
    
    def validate_priority(self, value):
        """Validate priority - required only for complaints"""
        request_type = self.initial_data.get('type')
        if request_type == 'complaint' and not value:
            raise serializers.ValidationError("Priority is required for complaints")
        if request_type != 'complaint' and value:
            raise serializers.ValidationError("Priority is only available for complaints")
        return value
    
    def validate_target_org(self, value):
        """Validate target organization - required only for complaints"""
        request_type = self.initial_data.get('type')
        if request_type == 'complaint' and not value:
            raise serializers.ValidationError("Organization must be specified for complaints")
        if request_type != 'complaint' and value:
            raise serializers.ValidationError("Organization selection is only available for complaints")
        return value
    
    def validate_description(self, value):
        """Validate issue description"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Issue description must be at least 10 characters long")
        return value.strip()


class HelpSupportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new support requests"""
    
    class Meta:
        model = HelpSupport
        fields = ['description', 'target_org', 'priority', 'type']
    
    def validate(self, attrs):
        """Validate data based on request type"""
        request_type = attrs.get('type')
        
        # For complaints
        if request_type == 'complaint':
            if not attrs.get('target_org'):
                raise serializers.ValidationError("Organization must be specified for complaints")
            if not attrs.get('priority'):
                raise serializers.ValidationError("Priority must be specified for complaints")
        
        # For general requests and account issues
        elif request_type in ['general', 'account']:
            if attrs.get('target_org'):
                raise serializers.ValidationError("Organization cannot be specified for this type of request")
            if attrs.get('priority'):
                raise serializers.ValidationError("Priority is only available for complaints")
        
        return attrs
    
class HelpSupportAdminSerializer(serializers.ModelSerializer):
    # بيانات المستخدم
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    
    # بيانات المؤسسة المستهدفة (إن وجدت)
    target_org_name = serializers.CharField(source='target_org.user.name', read_only=True)
    
    # عرض النصوص المقروءة للنوع والحالة
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = HelpSupport
        fields = [
            'id', 'user', 'user_name', 'user_email',
            'description', 'type_display',
            'priority', 'target_org', 'target_org_name',
            'status_display', 'reply',
            'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'status', 'type']


class OrganizationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationDocument
        fields = [
            "id",
            "registration_docs",
            "financial_report",
            "activity_proof",
            "address_proof",
            "created_at"
        ]
        read_only_fields = ["id", "created_at"]

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