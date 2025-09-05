from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken



from .models import (
    User, Announcement, AnnouncementCategory,
    AnnouncementEditRequest, UserFavorite, Organization, OrganizationDocument,
    Notification, HelpSupport
)

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

        org_data = {
            'description': validated_data.pop('description', ''),
            'website': validated_data.pop('website', ''),
            'location': validated_data.pop('location', ''),
            'rate': validated_data.pop('rate', 1),
            'verified': False,       
            'is_active': True,       
        }

        user = User.objects.create_user(
            email=validated_data['email'],
            password=password,
            name=validated_data.get('name', ''),
            phone=validated_data.get('phone', ''),
            profile_image=validated_data.get('profile_image', None),
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
    name = serializers.CharField(source='user.name', required=False)
    email = serializers.EmailField(source='user.email', required=False)
    phone = serializers.CharField(source='user.phone', required=False)
    profile_image = serializers.ImageField(source='user.profile_image', required=False)

    class Meta:
        model = Organization
        fields = [
            'name', 'email', 'phone', 'profile_image',
            'description', 'website', 'location', 'rate', 'verified', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['rate', 'verified', 'is_active', 'created_at', 'updated_at']

    def get_profile_image(self, obj):
        if obj.user.profile_image:
            request = self.context.get('request', None)
            if request:
                return request.build_absolute_uri(obj.user.profile_image.url)
            else:
                from django.conf import settings
                return f"{settings.BASE_URL}{obj.user.profile_image.url}"
        return None

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
    announcement_id = serializers.IntegerField(source="announcement.id", read_only=True)
    announcement_title = serializers.CharField(source="announcement.title", read_only=True)
    organization_name = serializers.CharField(source="announcement.organization.user.name", read_only=True)

    class Meta:
        model = UserFavorite
        fields = ['id', 'announcement_id', 'announcement_title', 'organization_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'announcement_id', 'announcement_title', 'organization_name', 'created_at', 'updated_at']

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
    """Improved serializer for listing announcements with conditional admin fields"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    organization_name = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()
    admin_notes = serializers.SerializerMethodField()
    image = serializers.ImageField(read_only=True)
    
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
        """Return admin_notes only for admin users, empty string for others"""
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user.role == User.Role.ADMIN:
            return obj.admin_notes or ""
        return ""


class AnnouncementDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed announcement view"""
    category = AnnouncementCategorySerializer(read_only=True)
    organization_name = serializers.SerializerMethodField()
    creator_name = serializers.SerializerMethodField()
    image = serializers.ImageField(read_only=True)
    
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


class AnnouncementEditRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating announcement edit requests"""
    # Make all proposed fields optional to allow partial edits
    proposed_title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    proposed_description = serializers.CharField(required=False, allow_blank=True)
    proposed_start_date = serializers.DateTimeField(required=False, allow_null=True)
    proposed_end_date = serializers.DateTimeField(required=False, allow_null=True)
    proposed_url = serializers.URLField(required=False, allow_blank=True)
    proposed_category = serializers.PrimaryKeyRelatedField(
        queryset=AnnouncementCategory.objects.all(),
        required=False,
        allow_null=True
    )
    proposed_image = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = AnnouncementEditRequest
        fields = [
            'original_announcement', 'proposed_title', 'proposed_description',
            'proposed_start_date', 'proposed_end_date', 'proposed_url', 'proposed_category',
            'proposed_image'
        ]
    
    def validate_original_announcement(self, value):
        """Ensure the announcement is approved and belongs to the requesting user's organization"""
        if value.status != Announcement.Status.APPROVED:
            raise serializers.ValidationError("Only approved announcements can have edit requests")
        
        user = self.context['request'].user
        if user.role == User.Role.ORGANIZATION:
            if value.created_by != user:
                raise serializers.ValidationError("You can only request edits for your own announcements")
        
        return value
    
    def validate(self, attrs):
        """Validate proposed dates and ensure at least one field is provided"""
        # Ensure at least one proposed field is provided
        proposed_fields = [
            'proposed_title', 'proposed_description', 'proposed_start_date',
            'proposed_end_date', 'proposed_url', 'proposed_category', 'proposed_image'
        ]
        
        if not any(field in attrs and attrs[field] is not None and attrs[field] != '' for field in proposed_fields):
            raise serializers.ValidationError(
                "At least one proposed field must be provided for the edit request."
            )
        
        # Validate proposed dates
        start_date = attrs.get('proposed_start_date')
        end_date = attrs.get('proposed_end_date')
        
        if start_date and end_date and end_date <= start_date:
            raise serializers.ValidationError("Proposed end date must be after start date")
        
        return attrs


class AnnouncementEditRequestListSerializer(serializers.ModelSerializer):
    """Serializer for listing announcement edit requests"""
    original_announcement_title = serializers.CharField(source='original_announcement.title', read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.name', read_only=True)
    requested_by_email = serializers.CharField(source='requested_by.email', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.name', read_only=True)
    
    class Meta:
        model = AnnouncementEditRequest
        fields = [
            'id', 'original_announcement_title', 'proposed_title', 'status',
            'requested_by_name', 'requested_by_email', 'reviewed_by_name',
            'created_at', 'reviewed_at'
        ]


class AnnouncementEditRequestDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed view of announcement edit requests"""
    original_announcement = AnnouncementDetailSerializer(read_only=True)
    requested_by_name = serializers.CharField(source='requested_by.name', read_only=True)
    requested_by_email = serializers.CharField(source='requested_by.email', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.name', read_only=True)
    proposed_category_name = serializers.CharField(source='proposed_category.name', read_only=True)
    
    class Meta:
        model = AnnouncementEditRequest
        fields = [
            'id', 'original_announcement', 'requested_by_name', 'requested_by_email',
            'proposed_title', 'proposed_description', 'proposed_start_date',
            'proposed_end_date', 'proposed_url', 'proposed_category', 'proposed_category_name',
            'proposed_image', 'status', 'admin_notes', 'reviewed_by_name', 'created_at', 
            'updated_at', 'reviewed_at'
        ]


class AnnouncementEditRequestApprovalSerializer(serializers.ModelSerializer):
    """Serializer for admin to approve/reject edit requests"""
    
    class Meta:
        model = AnnouncementEditRequest
        fields = ['status', 'admin_notes']
    
    def validate_status(self, value):
        if value not in [AnnouncementEditRequest.Status.APPROVED, AnnouncementEditRequest.Status.REJECTED]:
            raise serializers.ValidationError("Status must be either approved or rejected")
        return value
    
    def update(self, instance, validated_data):
        """Update edit request and apply changes if approved"""
        user = self.context['request'].user
        
        # Set review information
        instance.reviewed_by = user
        instance.reviewed_at = timezone.now()
        
        # Update status and notes
        instance.status = validated_data.get('status', instance.status)
        instance.admin_notes = validated_data.get('admin_notes', instance.admin_notes)
        instance.save()
        
        # Apply changes to original announcement if approved
        if instance.status == AnnouncementEditRequest.Status.APPROVED:
            instance.apply_changes()
        
        return instance


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
    target_org_name = serializers.CharField(source='target_org.user.name', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    status = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = HelpSupport
        fields = [
            'id', 'user', 'user_name', 'user_email', 'title', 'description',
            'target_org', 'target_org_name', 'type_display',
            'status', 'status_display', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'status', 'status_display']
    
    def validate_type(self, value):
        if value not in [choice[0] for choice in HelpSupport.SupportType.choices]:
            raise serializers.ValidationError("Invalid request type")
        return value
    
    def validate_target_org(self, value):
        request_type = self.initial_data.get('type')
        if request_type == HelpSupport.SupportType.ORGANIZATION and not value:
            raise serializers.ValidationError("Organization must be specified for organization requests")
        if request_type == HelpSupport.SupportType.SYSTEM and value is not None:
            raise serializers.ValidationError("Organization must not be specified for system issues")
        return value
    
    def validate_description(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Issue description must be at least 10 characters long")
        return value.strip()

class HelpSupportCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new support requests"""

    title = serializers.CharField(required=True)
    description = serializers.CharField(required=True)
    target_org = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        required=False,
        allow_null=True
    )
    type = serializers.ChoiceField(
        choices=HelpSupport.SupportType.choices,
        required=True
    )
    status = serializers.CharField(read_only=True, default=HelpSupport.Status.PENDING)

    class Meta:
        model = HelpSupport
        fields = ['title', 'description', 'target_org', 'type', 'status']

    def validate(self, attrs):
        request_type = attrs.get('type')

        # إذا كان من نوع "organization" يجب تحديد المؤسسة
        if request_type == HelpSupport.SupportType.ORGANIZATION:
            if not attrs.get('target_org'):
                raise serializers.ValidationError({
                    'target_org': "Organization must be specified for organization complaints."
                })

        # إذا كان من نوع "system" يجب عدم إدخال المؤسسة
        elif request_type == HelpSupport.SupportType.SYSTEM:
            if attrs.get('target_org') is not None:
                raise serializers.ValidationError({
                    'target_org': "Organization must not be specified for system issues."
                })

        # description و title مطلوبان دائمًا
        if not attrs.get('description'):
            raise serializers.ValidationError({'description': 'Description is required.'})
        if not attrs.get('title'):
            raise serializers.ValidationError({'title': 'Title is required.'})

        return attrs

class HelpSupportAdminSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    target_org_name = serializers.CharField(source='target_org.user.name', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    status = serializers.CharField(read_only=True)  # إضافة حالة الطلب

    class Meta:
        model = HelpSupport
        fields = [
            'id', 'user', 'user_name', 'user_email',
            'title', 'description', 'type_display',
            'target_org', 'target_org_name',
            'status', 'status_display', 'reply',
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
    
class OrganizationSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source="user.name", read_only=True)
    profile_image = serializers.ImageField(source="user.profile_image", read_only=True)
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

