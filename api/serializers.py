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

class AnnouncementCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AnnouncementCategory
        fields = "__all__"


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = "__all__"
        read_only_fields = ("created_at", "updated_at")


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
