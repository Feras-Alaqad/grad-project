from rest_framework import status, generics, viewsets, filters
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from rest_framework import permissions
from django.core.mail import send_mail, EmailMultiAlternatives
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.http import Http404
from rest_framework.exceptions import PermissionDenied
from rest_framework import status as drf_status
import os
from datetime import datetime, time
from django.utils.dateparse import parse_date, parse_datetime
from django.utils import timezone
from django.utils.translation import gettext as _, activate
from django.utils import translation
from django.http import JsonResponse


from .models import (
    User, Organization,
    Announcement,
    UserFavorite,
    HelpSupport,
    OrganizationDocument,
    Notification,
    UserApplicationTracking,
)
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.db.models.functions import TruncDay, TruncMonth
from .models import User, Organization, Announcement, AnnouncementCategory
from .email_utils import logo_header_html, banner_header_html, render_notification_email, render_welcome_email, render_admin_support_notification_email
from .serializers import (
    UserSignupSerializer,
    UserSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
    OrganizationSignupSerializer,
    OrganizationProfileSerializer,
    UserFavoriteSerializer,
    AnnouncementListSerializer,
    AnnouncementDetailSerializer,
    AnnouncementCreateSerializer,
    AnnouncementUpdateSerializer,
    AnnouncementAdminSerializer,
    AnnouncementApprovalSerializer,
    AnnouncementCategorySerializer,
    NotificationSerializer,
    OrganizationToggleActiveSerializer,
    LogoutSerializer,
    UserApplicationTrackingSerializer,
    HelpSupportAdminSerializer,
    HelpSupportSerializer,
    HelpSupportCreateSerializer,
    OrganizationDocumentSerializer,
    OrganizationSerializer,
    NotificationSerializer,
    NotificationDetailSerializer,
    NotificationToUserSerializer,
    NotificationListSerializer,
    OrganizationVerificationSerializer,
    OrganizationAdminSerializer
)



# =========================
# 🔹 Utility Functions
# =========================

def get_safe_profile_image_url(request, user):
    """
    Safely get profile image URL, fallback to default if file doesn't exist
    """
    if user.profile_image:
        # Check if the file actually exists
        file_path = os.path.join(settings.MEDIA_ROOT, str(user.profile_image))
        if os.path.exists(file_path):
            return settings.BASE_URL + user.profile_image.url
        else:
            # File doesn't exist, use default
            default_image_path = 'defaults/user_default.png'
            return settings.BASE_URL + settings.MEDIA_URL + default_image_path
    else:
        # No profile image set, use default
        default_image_path = 'defaults/user_default.png'
        return settings.BASE_URL + settings.MEDIA_URL + default_image_path

# =========================
# 🔹 Custom Permissions
# =========================

class IsAdminOrOrganization(BasePermission):
    """Permission for admin or organization users only"""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role in [User.Role.ADMIN, User.Role.ORGANIZATION]
        )

class IsAdminOnly(BasePermission):
    """Permission for admin users only"""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.role == User.Role.ADMIN
        )

class IsOwnerOrAdmin(BasePermission):
    """Permission for announcement owner or admin"""
    def has_object_permission(self, request, view, obj):
        return (
            request.user.is_authenticated and (
                obj.created_by == request.user or 
                request.user.role == User.Role.ADMIN
            )
        )


class UserSignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Send welcome notification and email
            try:
                from api.utils.notification_utils import NotificationManager
                notification_manager = NotificationManager(request)
                notification_manager.notify_welcome(user, is_organization=False)
            except Exception as e:
                # Log the error but don't fail the registration
                print(f"Failed to send welcome notification to {user.email}: {str(e)}")
            
            # إنشاء توكن وريفريش
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "success": True,
                    "message": "User created successfully",
                    "data": {
                        "user": {
                            "id": user.id,
                            "email": user.email,
                            "name": user.name,
                            "phone": user.phone,
                            "profile_image": get_safe_profile_image_url(request, user)
                        }
                    },
                    "refresh": str(refresh),
                    "access": str(refresh.access_token)
                },
                status=status.HTTP_201_CREATED
            )

        return Response({
            "success": False,
            "message": "Validation failed",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class OrganizationSignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OrganizationSignupSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save() 
            except ValueError as e:  
                return Response({
                    "success": False,
                    "message": "Validation failed",
                    "errors": str(e),  
                }, status=status.HTTP_400_BAD_REQUEST)

            # إنشاء التوكنات
            refresh = RefreshToken.for_user(user)
            access = refresh.access_token

            # إرسال بريد الترحيب للمنظمة
            try:
                from api.utils.notification_utils import NotificationManager
                notification_manager = NotificationManager(request)
                notification_manager.notify_welcome(user, is_organization=True)
            except Exception as e:
                # لا نريد أن يفشل التسجيل بسبب مشكلة في الإيميل
                print(f"Failed to send welcome notification to organization {user.email}: {str(e)}")

            return Response({
                "success": True,
                "message": "Organization registered successfully and account is active.",
                "data": {
                    "user": {
                        "id": user.id,
                        "email": user.email,
                        "role": user.role
                    }
                },
                "refresh": str(refresh),
                "access": str(access),
            }, status=status.HTTP_201_CREATED)

        return Response({
            "success": False,
            "message": "Validation failed",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)



class LogoutView(generics.GenericAPIView):
    serializer_class = LogoutSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)

class ForgotPasswordAPIView(generics.GenericAPIView):
    """
    API for requesting password reset
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({
            "success": False,
            "message": "Email is required."
        }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
            "success": False,
            "message": "No account found with this email."
        }, status=status.HTTP_404_NOT_FOUND)

        token = default_token_generator.make_token(user)

        reset_url = f"https://awn-three.vercel.app/reset-password/{user.id}/{token}/"

        # Use the new EmailService for better template rendering
        from api.services.email_service import EmailService
        email_service = EmailService(request)
        
        # Render using dedicated password reset template
        from django.template.loader import render_to_string
        context = {
            'user_name': user.name or user.email,
            'user_email': user.email,
            'reset_url': reset_url,
            'logo_url': email_service._get_logo_url(),
            'platform_url': getattr(settings, 'PLATFORM_URL', 'https://awn-three.vercel.app'),
        }
        html_message = render_to_string('emails/password_reset.html', context, request=request)
        
        # Plain text version
        message = f"""
Dear {user.name or user.email},

You requested to reset your password.

Click the link below to reset your password:
{reset_url}

Or copy this link into your browser.

Note: This link is valid for a limited time only.

Regards,
AWN Platform Security Team
"""

        try:
            # Use EmailMultiAlternatives to include both plain text and HTML with helpful headers
            email = EmailMultiAlternatives(
                subject="Reset Your AWN Platform Password",
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email],
                headers={
                    # Encourage clients to treat as transactional
                    "X-Entity-Type": "Transactional",
                    # Avoid replies going to the sending inbox
                    "Reply-To": "no-reply@awnpaltform.gmail.com"
                }
            )
            email.attach_alternative(html_message, "text/html")
            result = email.send(fail_silently=False)
            if result == 0:
                print("Password reset email send returned 0 (no recipients accepted)")
                return Response({
                    "success": False,
                    "message": "Email provider did not accept the message.",
                    "error": "EmailMultiAlternatives.send returned 0"
                }, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            # Log the error and return a proper response to help debugging
            print(f"Failed to send password reset email: {str(e)}")
            return Response({
                "success": False,
                "message": "Failed to send password reset email.",
                "error": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "success": True,
            "message": "Password reset link sent successfully. Check your email.",
            "data": {
                "email": user.email
            }
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])
def password_reset_email_preview(request):
    """
    Render the password reset email HTML for preview in browser.
    Useful for verifying logo visibility and font sizes.
    """
    # Sample data for preview
    sample_name = request.GET.get('name', 'AWN User')
    sample_email = request.GET.get('email', 'user@example.com')
    reset_url = request.GET.get(
        'reset_url',
        'https://awn-three.vercel.app/reset-password/12345/sample-token/'
    )

    html_preview = render_notification_email(
        title="Forgot your password?",
        message="To reset your password, click the button below. The link will self‑destruct after five days.",
        request=request,
        cta_url=reset_url,
        cta_label="Reset Password"
    )

    return HttpResponse(html_preview, content_type='text/html')


@api_view(['GET'])
@permission_classes([AllowAny])
def notification_email_preview(request):
    """Preview the brand-styled notification email in the browser.

    Query params:
    - title: email title
    - message: email message
    - cta_url: optional button URL
    - cta_label: optional button label
    """
    title = request.GET.get('title', 'Verify Your Account')
    message = request.GET.get(
        'message',
        'To finalize your setup and unlock all features, please verify your email address. This ensures the highest level of security for your account.'
    )
    cta_url = request.GET.get('cta_url')
    cta_label = request.GET.get('cta_label', 'Verify my email') if cta_url else None

    html = render_notification_email(title=title, message=message, request=request, cta_url=cta_url, cta_label=cta_label)
    from django.http import HttpResponse
    return HttpResponse(html, content_type='text/html')


@api_view(['GET'])
@permission_classes([AllowAny])
def support_reply_email_preview(request):
    """Preview the support reply email with a dedicated reply area.

    Query params:
    - reply: the reply text to show inside the reply box
    - title: support request title
    - user: user display name or email
    """
    reply = request.GET.get('reply', 'Thank you for contacting us. Your account has been verified. Please try logging in again and let us know if you face any issues.')
    sr_title = request.GET.get('title', 'Account Verification Issue')
    user_disp = request.GET.get('user', 'AWN User')

    html = render_notification_email(
        title=_('Support Reply'),
        message=(
            f"Dear {user_disp},\n\n"
            f"We have responded to your support request titled \"{sr_title}\".\n\n"
            "You can view this request and and the reply in the application under Support > My Requests.\n\n"
            "Best regards,\nAWN Platform Support Team"
        ),
        request=request,
        cta_url="https://awn-three.vercel.app/",
        cta_label=_('View My Requests'),
        reply_html=reply
    )
    from django.http import HttpResponse
    return HttpResponse(html, content_type='text/html')


class ResetPasswordAPIView(generics.GenericAPIView):
    serializer_class = ResetPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.context['user']
        new_password = serializer.validated_data['password']
        user.set_password(new_password)
        user.save()

        return Response({
            'success': True,
            'message': 'Password reset successful',
            'data': {
                'user_email': user.email
            }
        }, status=status.HTTP_200_OK)


class ChangePasswordAPIView(generics.GenericAPIView):
    """
    API for changing password for logged-in user
    """
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        new_password = serializer.validated_data['new_password']
        user.set_password(new_password)
        user.save()

        return Response({
            'success': True,
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)
    
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role == user.Role.ORGANIZATION:
            try:
                organization = Organization.objects.get(user=user)
            except Organization.DoesNotExist:
                return Response({
                    "success": False,
                    "message": "Organization profile not found"
                }, status=404)
            
            serializer = OrganizationProfileSerializer(organization, context={'request': request})
            return Response({
                "success": True,
                "message": "Organization profile retrieved successfully",
                "data": serializer.data
            })
        
        # للمستخدم العادي
        else:
            serializer = UserSerializer(user, context={'request': request})
            return Response({
                "success": True,
                "message": "User profile retrieved successfully",
                "data": serializer.data
            })

    def put(self, request):
        user = request.user

        # حقول ممنوعة للمستخدم العادي
        forbidden_fields_user = ['description', 'website', 'location', 'role']

        # USER العادي
        if user.role == user.Role.USER:
            for field in forbidden_fields_user:
                if field in request.data:
                    return Response(
                        {"detail": f"You are not allowed to update the field '{field}'."},
                        status=403
                    )

            # التحقق من البريد قبل الحفظ
            email = request.data.get('email')
            if email and User.objects.exclude(pk=user.pk).filter(email=email).exists():
                return Response({"email": ["This email is already used by another account."]}, status=400)

            # تحديث بيانات User العادية
            for field in ['name', 'email', 'phone', 'profile_image']:
                if field in request.data:
                    setattr(user, field, request.data[field])
            user.save()
            
            # إرجاع البيانات مع الرابط الكامل للصورة
            return Response({
                "success": True,
                "message": "Profile updated successfully",
                "data": UserSerializer(user, context={'request': request}).data
            })

        # ORGANIZATION
        elif user.role == user.Role.ORGANIZATION:
            try:
                organization = Organization.objects.get(user=user)
            except Organization.DoesNotExist:
                return Response({
                    "success": False,
                    "message": "Organization profile not found"
                }, status=404)

            # منع تعديل role
            if 'role' in request.data:
                return Response({"detail": "You cannot change your role."}, status=403)

            # التحقق من البريد قبل الحفظ
            email = request.data.get('email')
            if email and User.objects.exclude(pk=user.pk).filter(email=email).exists():
                return Response({"email": ["This email is already used by another account."]}, status=400)

            # تحديث بيانات المؤسسة باستخدام الـ serializer (يتضمن profile_image و user fields)
            serializer = OrganizationProfileSerializer(
                organization, data=request.data, partial=True, context={'request': request}
            )
            if serializer.is_valid():
                serializer.save()
                return Response({
                    "success": True,
                    "message": "Organization profile updated successfully",
                    "data": serializer.data
                })
            return Response({
                "success": False,
                "message": "Validation error",
                "errors": serializer.errors
            }, status=400)

        # Admin أو أدوار أخرى
        else:
            serializer = UserSerializer(user, data=request.data, partial=True, context={'request': request})
            if serializer.is_valid():
                serializer.save()
                return Response({
                    "success": True,
                    "message": "Profile updated successfully",
                    "data": serializer.data
                })
            return Response({
                "success": False,
                "message": "Validation error",
                "errors": serializer.errors
            }, status=400)

# =========================
# 🔹 Announcement Views
# =========================

class AnnouncementCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for announcement categories with create functionality"""
    queryset = AnnouncementCategory.objects.all()
    serializer_class = AnnouncementCategorySerializer
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAdminOnly]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]


class AnnouncementViewSet(viewsets.ModelViewSet):
    """ViewSet for announcements with different permissions"""
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['id', 'category', 'organization', 'status']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'start_date', 'end_date']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        action = getattr(self, 'action', None)

        # Admin can see everything across all actions
        if user.is_authenticated and user.role == User.Role.ADMIN:
            return Announcement.objects.all()

        # Public list: only approved announcements
        if action == 'list':
            return Announcement.objects.filter(status=Announcement.Status.APPROVED)

        # Detail retrieval:
        # - Organizations can see their own announcements by ID regardless of status
        # - Other authenticated users and anonymous users see only approved
        if action == 'retrieve':
            if user.is_authenticated and user.role == User.Role.ORGANIZATION:
                return Announcement.objects.filter(
                    Q(status=Announcement.Status.APPROVED) |
                    Q(created_by=user) |
                    Q(organization__user=user)
                )
            else:
                return Announcement.objects.filter(status=Announcement.Status.APPROVED)

        # Other actions
        if user.is_authenticated:
            if user.role == User.Role.ORGANIZATION:
                # Organizations operating on their own collections
                return Announcement.objects.filter(created_by=user)
            else:
                return Announcement.objects.filter(status=Announcement.Status.APPROVED)

        return Announcement.objects.filter(status=Announcement.Status.APPROVED)

    def get_serializer_class(self):
        if self.action == 'list':
            return AnnouncementListSerializer
        elif self.action == 'retrieve':
            return AnnouncementDetailSerializer
        elif self.action == 'create':
            return AnnouncementCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AnnouncementUpdateSerializer
        elif self.action == 'approve':
            return AnnouncementApprovalSerializer
        else:
            return AnnouncementListSerializer  # Use improved serializer instead of admin-only

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        elif self.action == 'create':
            permission_classes = [IsAdminOnly]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsOwnerOrAdmin]
        elif self.action in ['approve', 'pending_announcements']:
            permission_classes = [IsAdminOnly]
        else:
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def list(self, request, *args, **kwargs):
        """Override list to return standard format with validation for ID filter"""
        # Check if filtering by ID
        id_filter = request.query_params.get('id')

        if id_filter:
            # When filtering by a specific ID, expand permissions for organization owners
            user = request.user
            base_qs = Announcement.objects.filter(pk=id_filter)

            if user.is_authenticated and user.role == User.Role.ADMIN:
                queryset = base_qs
            elif user.is_authenticated and user.role == User.Role.ORGANIZATION:
                queryset = base_qs.filter(
                    Q(status=Announcement.Status.APPROVED) |
                    Q(created_by=user) |
                    Q(organization__user=user)
                )
            else:
                queryset = base_qs.filter(status=Announcement.Status.APPROVED)

            if not queryset.exists():
                return Response({
                    'success': False,
                    'message': f'No announcement found with ID: {id_filter}'
                }, status=status.HTTP_404_NOT_FOUND)
        else:
            # Default list behavior with filters (approved-only for public/non-admin)
            queryset = self.filter_queryset(self.get_queryset())
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                'success': True,
                'data': serializer.data
            })
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to handle not found errors with custom message"""
        # Custom object retrieval to allow organization owners to access pending announcements
        pk = kwargs.get('pk')
        user = request.user
        try:
            base_qs = Announcement.objects.filter(pk=pk)
            if user.is_authenticated and user.role == User.Role.ADMIN:
                instance = base_qs.first()
            elif user.is_authenticated and user.role == User.Role.ORGANIZATION:
                instance = base_qs.filter(
                    Q(status=Announcement.Status.APPROVED) |
                    Q(created_by=user) |
                    Q(organization__user=user)
                ).first()
            else:
                instance = base_qs.filter(status=Announcement.Status.APPROVED).first()

            if not instance:
                raise Http404

            serializer = self.get_serializer(instance)
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Http404:
            return Response({
                'success': False,
                'message': f'No announcement found with ID: {pk}'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['patch'], url_path='approve')
    def approve(self, request, pk=None):
        """Admin action to approve/reject announcements"""
        announcement = self.get_object()
        serializer = self.get_serializer(announcement, data=request.data, partial=True)
        
        if serializer.is_valid():
            old_status = announcement.status
            serializer.save()
            
            from api.utils.notification_utils import NotificationManager
            notification_manager = NotificationManager(request)
            
            # Send notification to organization user about status change
            status_display = (announcement.status or "").title()
            target_user = None
            
            if getattr(announcement, "organization", None) and getattr(announcement.organization, "user", None):
                target_user = announcement.organization.user
            elif announcement.created_by and announcement.created_by.role == User.Role.ORGANIZATION:
                target_user = announcement.created_by
            
            created_notification = None
            if target_user:
                created_notification = notification_manager.notify_announcement_status_change(
                    announcement=announcement,
                    organization_user=target_user,
                    status=announcement.status,
                    admin_notes=announcement.admin_notes
                )
            
            # If announcement was just approved, notify all users
            if announcement.status == Announcement.Status.APPROVED and old_status != Announcement.Status.APPROVED:
                try:
                    # Get all regular users
                    all_users = User.objects.filter(role=User.Role.USER, is_active=True)
                    
                    # Notify all users about new announcement
                    notification_manager.notify_announcement_approved(
                        announcement=announcement,
                        users=list(all_users)
                    )
                    
                    print(f"Notified {all_users.count()} users about new announcement: {announcement.title}")
                except Exception as e:
                    print(f"Failed to notify users about new announcement: {str(e)}")
            
            return Response({
                'success': True,
                'message': f"Announcement {status_display.lower()} successfully",
                'data': AnnouncementAdminSerializer(announcement).data,
                'notification': (NotificationDetailSerializer(created_notification).data if created_notification else None)
            }, status=status.HTTP_200_OK)
        return Response({
            'success': False,
            'message': 'Validation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='pending')
    def pending_announcements(self, request):

        """Admin action to get pending announcements"""

        pending = Announcement.objects.filter(status=Announcement.Status.PENDING)
        serializer = AnnouncementListSerializer(pending, many=True, context={'request': request})
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='my-announcements')
    def my_announcements(self, request):
        """Get current user's announcements
        - Includes admin-created announcements targeted to the user's existing organization
        
        """
        if not request.user.is_authenticated:
            return Response({
                'success': False,
                'message': 'Authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)

        org_id = request.query_params.get('organization_id')

        if org_id:
            # Fetch announcements for a specific organization with authorization checks
            try:
                organization = Organization.objects.get(id=org_id)
            except Organization.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'Organization not found'
                }, status=status.HTTP_404_NOT_FOUND)

            # Only admins or the organization owner can view this organization's announcements
            if not (request.user.role == User.Role.ADMIN or organization.user_id == request.user.id):
                return Response({
                    'success': False,
                    'message': "Not authorized to view this organization's announcements"
                }, status=status.HTTP_403_FORBIDDEN)

            announcements = Announcement.objects.filter(
                Q(organization=organization) &
                (Q(created_by=request.user) | Q(created_by__role=User.Role.ADMIN))
            )
        else:
            # Default: user's own announcements and admin-created ones for their organization (if org user)
            base_q = Q(created_by=request.user)

            if request.user.role == User.Role.ORGANIZATION:
                org = Organization.objects.filter(user=request.user).first()
                if org:
                    base_q = base_q | (Q(created_by__role=User.Role.ADMIN) & Q(organization=org))

            announcements = Announcement.objects.filter(base_q)

        serializer = AnnouncementListSerializer(announcements.order_by('-created_at'), many=True, context={'request': request})
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        """Override to set created_by field and notify org if pending"""
        instance = serializer.save(created_by=self.request.user)

        # Only send pending notification to organization users who created the announcement
        if (self.request.user.is_authenticated and 
            self.request.user.role == User.Role.ORGANIZATION and
            instance.created_by == self.request.user):
            if instance.status == Announcement.Status.PENDING:
                Notification.objects.create(
                    user=self.request.user,
                    title=f"Pending Announcement: {instance.title}",
                    message="Your announcement has been submitted and is pending for admin review."
                )

    def perform_update(self, serializer):
        """Notify org when their edit moves status to pending"""
        prev_status = serializer.instance.status
        instance = serializer.save()

        # Only send pending notification to organization users who own the announcement
        if (self.request.user.is_authenticated and 
            self.request.user.role == User.Role.ORGANIZATION and
            instance.created_by == self.request.user):
            if instance.status == Announcement.Status.PENDING and prev_status != Announcement.Status.PENDING:
                Notification.objects.create(
                    user=self.request.user,
                    title=f"Pending Announcement: {instance.title}",
                    message="Your announcement update is pending for admin review."
                )
    
    @action(detail=True, methods=['post', 'delete', 'get'], url_path='track-application', permission_classes=[IsAuthenticated])
    def track_application(self, request, pk=None):
        """
        Track or remove user application status and set reminders
        POST /api/announcements/{id}/track-application/ - Create or update tracking
        DELETE /api/announcements/{id}/track-application/ - Remove tracking
        GET /api/announcements/{id}/track-application/ - Retrieve current user's tracking for this announcement
        
        Expected payload for POST:
        {
            "status": "applied",  // optional, defaults to 'not applied'
            "notes": "Application submitted successfully",
            "reminder_date": "2024-02-15T10:00:00Z"  // optional
        }
        """
        # Check if user has 'user' role
        if request.user.role != User.Role.USER:
            return Response({
                'success': False,
                'message': 'Only users with user role can track applications'
            }, status=status.HTTP_403_FORBIDDEN)
        
        announcement = self.get_object()
        
        # Handle GET request
        if request.method == 'GET':
            try:
                tracking = UserApplicationTracking.objects.get(
                    user=request.user,
                    announcement=announcement
                )
                serializer = UserApplicationTrackingSerializer(tracking)
                return Response({
                    'success': True,
                    'data': serializer.data
                }, status=status.HTTP_200_OK)
            except UserApplicationTracking.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'No tracking record found for this announcement'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Handle DELETE request
        if request.method == 'DELETE':
            try:
                tracking = UserApplicationTracking.objects.get(
                    user=request.user,
                    announcement=announcement
                )
                tracking.delete()
                return Response({
                    'success': True,
                    'message': 'Application tracking removed successfully'
                }, status=status.HTTP_200_OK)
            except UserApplicationTracking.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'No tracking record found for this announcement'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Handle POST request
        # Normalize reminder_date to a timezone-aware datetime if provided
        raw_reminder = request.data.get('reminder_date')
        reminder_dt = None
        if raw_reminder:
            if isinstance(raw_reminder, str):
                dt = parse_datetime(raw_reminder)
                if dt is None:
                    d = parse_date(raw_reminder)
                    if d is not None:
                        dt = datetime.combine(d, time.min)
                if dt is not None:
                    if timezone.is_naive(dt):
                        dt = timezone.make_aware(dt, timezone.get_current_timezone())
                    reminder_dt = dt
            else:
                # Try interpreting as epoch seconds
                try:
                    reminder_dt = datetime.fromtimestamp(float(raw_reminder), tz=timezone.get_current_timezone())
                except Exception:
                    reminder_dt = None

        # Check if tracking already exists for this user and announcement
        tracking, created = UserApplicationTracking.objects.get_or_create(
            user=request.user,
            announcement=announcement,
            defaults={
                'status': request.data.get('status', 'not applied'),
                'notes': request.data.get('notes', ''),
                'reminder_date': reminder_dt
            }
        )
        
        if not created:
            # Update existing tracking
            if 'status' in request.data:
                tracking.status = request.data.get('status')
            if 'notes' in request.data:
                tracking.notes = request.data.get('notes')
            if 'reminder_date' in request.data:
                tracking.reminder_date = reminder_dt
            tracking.save()
        
        serializer = UserApplicationTrackingSerializer(tracking)
        return Response({
            'success': True,
            'message': 'Application tracking updated successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    

    
    @action(detail=False, methods=['get'], url_path='my-applications', permission_classes=[IsAuthenticated])
    def my_applications(self, request):
        """
        Get user's tracked applications from database
        GET /api/announcements/my-applications/
        """
        # Check if user has 'user' role
        if request.user.role != User.Role.USER:
            return Response({
                'success': False,
                'message': 'Only users with user role can view their applications'
            }, status=status.HTTP_403_FORBIDDEN)
        
        applications = UserApplicationTracking.objects.filter(user=request.user)
        serializer = UserApplicationTrackingSerializer(applications, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'data': serializer.data,
            'count': applications.count()
        }, status=status.HTTP_200_OK)
    



# =========================
# 🔹 Dedicated Announcement Creation View
# =========================

class CreateAnnouncementsView(APIView):
    """
    Dedicated view for announcement creation and listing
    GET: List announcements (with filtering)
    POST: Create new announcement (admin/organization only)
    """
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Different permissions for different methods"""
        if self.request.method == 'POST':
            return [IsAdminOnly()]
        return [IsAuthenticated()]
    
    def get(self, request):
        """
        This endpoint is deprecated for listing announcements.
        Use /awn/api/announcements/ for viewing announcements with filtering.
        """
        return Response({
            'success': False,
            'message': 'Use /awn/api/announcements/ for viewing announcements with filtering capabilities.',
            'redirect_to': '/awn/api/announcements/'
        }, status=status.HTTP_301_MOVED_PERMANENTLY)
    
    def post(self, request):
        """
        Create new announcement
        Only admin and organization users can create announcements
        """
        serializer = AnnouncementCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            # Set the creator, it will retuen the name of the creator of the announcement, if admin it will retuen the admin name, so condider this to do not view it or i will remove it in the production version //mhnd
            announcement = serializer.save(created_by=request.user)
            
            # If admin creates an approved announcement, notify all users
            if announcement.status == Announcement.Status.APPROVED and request.user.role == User.Role.ADMIN:
                try:
                    from api.utils.notification_utils import NotificationManager
                    notification_manager = NotificationManager(request)
                    
                    # Get all regular users
                    all_users = User.objects.filter(role=User.Role.USER, is_active=True)
                    
                    # Notify all users about new announcement
                    notification_manager.notify_announcement_approved(
                        announcement=announcement,
                        users=list(all_users)
                    )
                    
                    print(f"Notified {all_users.count()} users about new admin announcement: {announcement.title}")
                except Exception as e:
                    print(f"Failed to notify users about new announcement: {str(e)}")
            
            # Return detailed response
            response_serializer = AnnouncementDetailSerializer(announcement)
            
            return Response({
                'success': True,
                'message': 'Announcement created successfully',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': 'Validation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class DeleteAnnouncementView(APIView):
    """
    Delete announcement view - allows organizations and admins to delete announcements
    DELETE: Delete announcement (organization owner or admin only)
    """
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        """Get announcement with permission checks"""
        try:
            announcement = Announcement.objects.get(pk=pk)
            
            # Admin can delete any announcement
            if self.request.user.role == User.Role.ADMIN:
                return announcement
            
            # Organization can only delete their own announcements
            if self.request.user.role == User.Role.ORGANIZATION:
                # Get the organization associated with this user
                try:
                    organization = self.request.user.organizations.first()
                    if organization and announcement.organization == organization:
                        return announcement
                except Exception:
                    pass
            
            # Normal users cannot delete announcements
            return None
            
        except Announcement.DoesNotExist:
            return None
    
    def delete(self, request, pk):
        """
        Delete announcement - organizations and admins only
        """
        # Check if user has permission to delete announcements
        if request.user.role == User.Role.USER:
            return Response({
                'success': False,
                'message': 'Normal users cannot delete announcements'
            }, status=status.HTTP_403_FORBIDDEN)
        
        announcement = self.get_object(pk)
        
        if not announcement:
            return Response({
            'success': False,
            'message': 'Announcement not found or permission denied'
        }, status=status.HTTP_404_NOT_FOUND)
        
        # Store announcement title for response
        announcement_title = announcement.title
        
        # Delete the announcement
        announcement.delete()
        
        return Response({
            'success': True,
            'message': f'Announcement "{announcement_title}" deleted successfully'
        }, status=status.HTTP_200_OK)





class OrganizationSearchView(APIView):
    """
    API endpoint for searching organizations by name or email.
    Accessible by users with role 'user' or 'admin'.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Search organizations by name or email"""
        user = request.user

        # ✅ allow only user or admin roles
        if user.role not in [user.Role.USER, user.Role.ADMIN]:
            return Response({
                'success': False,
                'message': 'You are not allowed to search organizations'
            }, status=status.HTTP_403_FORBIDDEN)

        search_query = request.query_params.get('q', '').strip()
        if not search_query:
            return Response({
                'success': False,
                'message': 'Search query parameter "q" is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        organizations = Organization.objects.filter(
            Q(user__name__icontains=search_query) |
            Q(user__email__icontains=search_query)
        ).select_related("user")[:10]

        serializer = OrganizationSerializer(
            organizations, many=True, context={"request": request}
        )

        return Response({
            'success': True,
            'message': 'Organizations found',
            'data': serializer.data
        }, status=status.HTTP_200_OK)


# =========================
# 🔹 Admin Organization Management
# =========================




class UpdateAnnouncementView(APIView):
    """
    Dedicated view for updating announcements with complex workflow:
    - Unapproved announcements: Direct edit
    - Approved announcements: Create edit request for admin approval
    PUT/PATCH: Update announcement (owner or admin only)
    """
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk):
        """Get announcement object with permission check"""
        try:
            announcement = Announcement.objects.get(pk=pk)
            
            # Check permissions
            if (self.request.user.role == User.Role.ADMIN or 
                announcement.created_by == self.request.user):
                return announcement
            else:
                return None
        except Announcement.DoesNotExist:
            return None
    
    def _handle_approved_announcement_edit(self, announcement, request_data, partial=False):
        """Handle edit for approved announcements - set status to PENDING"""
        # Update the announcement directly but set status to PENDING for admin review
        serializer = AnnouncementUpdateSerializer(
            announcement, 
            data=request_data, 
            partial=partial, 
            context={'request': self.request}
        )
        
        if serializer.is_valid():
            # Set status to PENDING when organization edits an approved announcement
            updated_announcement = serializer.save(status=Announcement.Status.PENDING)
            response_serializer = AnnouncementDetailSerializer(updated_announcement)

            # Create a notification to inform the organization user that edit is pending
            target_user = None
            if getattr(updated_announcement, 'organization', None) and getattr(updated_announcement.organization, 'user', None):
                target_user = updated_announcement.organization.user
            elif updated_announcement.created_by and updated_announcement.created_by.role == User.Role.ORGANIZATION:
                target_user = updated_announcement.created_by

            created_notification = None
            if target_user:
                created_notification = Notification.objects.create(
                    user=target_user,
                    title=f"Pending Announcement: {updated_announcement.title}",
                    message="Your announcement update is pending admin review."
                )
            
            return Response({
                'success': True,
                'message': 'Announcement updated successfully. Status set to pending for admin review.',
                'data': response_serializer.data,
                'notification': (NotificationDetailSerializer(created_notification).data if created_notification else None)
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': 'Validation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def _handle_direct_update(self, announcement, request_data, partial=False):
        """Handle direct update for unapproved announcements or admin updates"""
        serializer = AnnouncementUpdateSerializer(
            announcement, 
            data=request_data, 
            partial=partial, 
            context={'request': self.request}
        )
        
        if serializer.is_valid():
            # For admin updates, allow setting status and admin_notes directly
            updated_announcement = serializer.save()

            # If admin provided status/admin_notes in request, reflect it
            admin_set_status = request_data.get('status')
            admin_notes = request_data.get('admin_notes')

            if self.request.user.role == User.Role.ADMIN and (admin_set_status or admin_notes is not None):
                # Apply status and notes if present
                if admin_set_status:
                    updated_announcement.status = admin_set_status
                if admin_notes is not None:
                    updated_announcement.admin_notes = admin_notes
                updated_announcement.save(update_fields=['status', 'admin_notes', 'updated_at'])

                # Determine target organization user
                target_user = None
                if getattr(updated_announcement, 'organization', None) and getattr(updated_announcement.organization, 'user', None):
                    target_user = updated_announcement.organization.user
                elif updated_announcement.created_by and updated_announcement.created_by.role == User.Role.ORGANIZATION:
                    target_user = updated_announcement.created_by

                created_notification = None
                if target_user:
                    status_display = (updated_announcement.status or '').title()
                    created_notification = Notification.objects.create(
                        user=target_user,
                        title=(f"{status_display}: {updated_announcement.title}" if status_display else f"Status: {updated_announcement.title}"),
                        message=(updated_announcement.admin_notes.strip() if updated_announcement.admin_notes else f"Your announcement '{updated_announcement.title}' was {status_display.lower() if status_display else 'updated'} by admin.")
                    )

                response_serializer = AnnouncementDetailSerializer(updated_announcement)
                return Response({
                    'success': True,
                    'message': f"Announcement {updated_announcement.status.lower() if updated_announcement.status else 'updated'} successfully",
                    'data': response_serializer.data,
                    'notification': (NotificationDetailSerializer(created_notification).data if created_notification else None)
                }, status=status.HTTP_200_OK)

            # Default response for non-admin or no status change
            response_serializer = AnnouncementDetailSerializer(updated_announcement)
            return Response({
                'success': True,
                'message': 'Announcement updated successfully',
                'data': response_serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'message': 'Validation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, pk):
        """Full update of announcement"""
        announcement = self.get_object(pk)
        
        if not announcement:
            return Response({
                'success': False,
                'message': 'Announcement not found or permission denied'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if this is an approved announcement and user is organization
        if (announcement.status == Announcement.Status.APPROVED and 
            request.user.role == User.Role.ORGANIZATION):
            return self._handle_approved_announcement_edit(announcement, request.data, partial=False)
        else:
            # Direct update for unapproved announcements or admin updates
            return self._handle_direct_update(announcement, request.data, partial=False)
    
    def patch(self, request, pk):
        """Partial update of announcement"""
        announcement = self.get_object(pk)
        
        if not announcement:
            return Response({
                'success': False,
                'message': 'Announcement not found or permission denied'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if this is an approved announcement and user is organization
        if (announcement.status == Announcement.Status.APPROVED and 
            request.user.role == User.Role.ORGANIZATION):
            return self._handle_approved_announcement_edit(announcement, request.data, partial=True)
        else:
            # Direct update for unapproved announcements or admin updates
            return self._handle_direct_update(announcement, request.data, partial=True)
        


class OrganizationCreateAnnouncementView(APIView):
    """
    Dedicated view for organizations to create announcements
    POST: Create new announcement (organization only)
    """
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Only organizations can create announcements through this endpoint"""
        return [IsAuthenticated()]
    
    def post(self, request):
        """
        Create new announcement - organizations only
        """
        # Check if user is an organization
        if request.user.role != User.Role.ORGANIZATION:
            return Response({
                'success': False,
                'message': 'Only organizations can create announcements through this endpoint'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get the organization associated with this user
        try:
            organization = request.user.organizations.first()
            if not organization:
                
                org_count = request.user.organizations.count()
                return Response({
                    'success': False,
                    'message': f'No organization found for this user. User ID: {request.user.id}, Role: {request.user.role}, Organization count: {org_count}'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'message': f'Error retrieving organization information: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = AnnouncementCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            # Set the creator and organization
            announcement = serializer.save(
                created_by=request.user,
                organization=organization
            )

            # Create a notification for the organization when status is pending
            if announcement.status == Announcement.Status.PENDING:
                target_user = organization.user if getattr(organization, 'user', None) else request.user
                created_notification = Notification.objects.create(
                    user=target_user,
                    title=f"Pending Announcement: {announcement.title}",
                    message="Your announcement has been submitted and it is pending for admin review."
                )
            
            # Return detailed response
            response_serializer = AnnouncementDetailSerializer(announcement)
            
            return Response({
                'success': True,
                'message': 'Announcement created successfully',
                'data': response_serializer.data,
                'notification': (NotificationDetailSerializer(created_notification).data if announcement.status == Announcement.Status.PENDING else None)
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': 'Validation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class AddFavoriteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, announcement_id):
        user = request.user
        try:
            announcement = Announcement.objects.get(id=announcement_id)
        except Announcement.DoesNotExist:
            return Response({
                "success": False,
                "message": "Announcement not found."
            }, status=status.HTTP_404_NOT_FOUND)

        # التحقق من دور اليوزر
        if user.role != User.Role.USER:
            return Response({
                "success": False,
                "message": "Only users with role 'user' can add favorites."
            }, status=status.HTTP_403_FORBIDDEN)

        favorite, created = UserFavorite.objects.get_or_create(
            announcement=announcement,
            user=user
        )

        serializer = UserFavoriteSerializer(favorite, context={'request': request})
        return Response({
            "success": True,
            "message": "Added to favorites successfully" if created else "Already in favorites",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class RemoveFavoriteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, announcement_id):
        user = request.user

        if user.role != User.Role.USER:
            return Response({
                "success": False,
                "message": "Only users with role 'user' can remove favorites."
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            favorite = UserFavorite.objects.get(announcement__id=announcement_id, user=user)
        except UserFavorite.DoesNotExist:
            return Response({
                "success": False,
                "message": "Favorite not found."
            }, status=status.HTTP_404_NOT_FOUND)

        favorite.delete()

        return Response({
            "success": True,
            "message": "Announcement removed from favorites."
        }, status=status.HTTP_200_OK)


class ListFavoritesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role != User.Role.USER:
            return Response({
                "success": False,
                "message": "Only users with role 'user' can view favorites."
            }, status=status.HTTP_403_FORBIDDEN)

        favorites = UserFavorite.objects.filter(user=user).order_by('-created_at')
        serializer = UserFavoriteSerializer(favorites, many=True, context={'request': request})
        
        return Response({
            "success": True,
            "data": serializer.data
        }, status=status.HTTP_200_OK)


class OrganizationToggleActiveView(generics.RetrieveUpdateAPIView):
    queryset = Organization.objects.all()
    serializer_class = OrganizationToggleActiveSerializer
    permission_classes = [IsAdminOnly]

class ToggleBlockUserAPIView(APIView):
    permission_classes = [IsAdminOnly] 

    def patch(self, request, user_id):

        user = get_object_or_404(User, id=user_id)

        if user.role == "admin":
            return Response(
                {"success": False, "message": "Cannot block/unblock an admin user."},
                status=status.HTTP_403_FORBIDDEN
            )

        # تغيير حالة التفعيل
        user.is_active = not user.is_active
        user.save()

        status_str = "unblocked" if user.is_active else "blocked"
        return Response(
            {"success": True, "message": f"User {user.email} has been {status_str}."},
            status=status.HTTP_200_OK
        )

class UserListAPIView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAdminOnly]

    def get_queryset(self):
        queryset = User.objects.all().order_by('-created_at')
        role = self.request.query_params.get('role', None)
        if role in ['user', 'organization', 'admin']:
            queryset = queryset.filter(role=role)
        return queryset
    
class UserDetailAPIView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAdminOnly]  
    queryset = User.objects.all()
    lookup_field = 'id'

class UserSearchAPIView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAdminOnly] 

    def get_queryset(self):
        query = self.request.query_params.get('q', '').strip()
        if not query:
            return User.objects.none()  # لو لم يتم تمرير q
        return User.objects.filter(
            Q(name__icontains=query) | Q(email__icontains=query)
        ).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        if "q" not in request.query_params or not request.query_params.get("q").strip():
            return Response(
                {"success": False, "message": 'Search query parameter "q" is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().list(request, *args, **kwargs)

class IsUserRole(permissions.BasePermission):
    """Permission to ensure user has 'user' role"""
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == User.Role.USER
        )

class IsAdminRole(permissions.BasePermission):
    """
    Permission للتحقق أن المستخدم لديه دور ADMIN
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == User.Role.ADMIN
        )

class IsOrganizationRole(permissions.BasePermission):
    """
    Permission للتحقق أن المستخدم لديه دور ORGANIZATION
    """
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.role == User.Role.ORGANIZATION
        )
    
class AdminStatisticsAPIView(APIView):
    """
    Return aggregate statistics for the application. Accessible to admin users only.
    Includes totals across core models and key status breakdowns.
    """
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        # Optional date range filters: start_date, end_date (YYYY-MM-DD)
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        start_dt = None
        end_dt = None
        if start_date_str:
            sd = parse_date(start_date_str)
            if sd:
                start_dt = timezone.make_aware(datetime.combine(sd, time.min))
        if end_date_str:
            ed = parse_date(end_date_str)
            if ed:
                end_dt = timezone.make_aware(datetime.combine(ed, time.max))

        def apply_date_filters(qs):
            if start_dt and end_dt:
                return qs.filter(created_at__gte=start_dt, created_at__lte=end_dt)
            if start_dt:
                return qs.filter(created_at__gte=start_dt)
            if end_dt:
                return qs.filter(created_at__lte=end_dt)
            return qs

        # Users
        users_total = apply_date_filters(User.objects.all()).count()
        users_active = apply_date_filters(User.objects.filter(is_active=True)).count()
        users_by_role = {
            'admin': apply_date_filters(User.objects.filter(role=User.Role.ADMIN)).count(),
            'organization': apply_date_filters(User.objects.filter(role=User.Role.ORGANIZATION)).count(),
            'user': apply_date_filters(User.objects.filter(role=User.Role.USER)).count(),
        }

        # Organizations
        org_total = apply_date_filters(Organization.objects.all()).count()
        org_verified = apply_date_filters(Organization.objects.filter(verified=True)).count()
        org_active = apply_date_filters(Organization.objects.filter(is_active=True)).count()
        org_blocked = apply_date_filters(Organization.objects.filter(is_active=False)).count()

        # Announcements
        # Count only approved announcements in total to reflect published items
        ann_total = apply_date_filters(Announcement.objects.filter(status=Announcement.Status.APPROVED)).count()
        ann_by_status = {
            'approved': apply_date_filters(Announcement.objects.filter(status=Announcement.Status.APPROVED)).count(),
            'pending': apply_date_filters(Announcement.objects.filter(status=Announcement.Status.PENDING)).count(),
            'rejected': apply_date_filters(Announcement.objects.filter(status=Announcement.Status.REJECTED)).count(),
            'draft': apply_date_filters(Announcement.objects.filter(status=Announcement.Status.DRAFT)).count(),
        }

        # Categories
        categories_total = AnnouncementCategory.objects.count()

        # Favorites
        favorites_total = apply_date_filters(UserFavorite.objects.all()).count()

        # Organization Documents
        docs_total = apply_date_filters(OrganizationDocument.objects.all()).count()
        docs_by_status = {
            'approved': apply_date_filters(OrganizationDocument.objects.filter(status='approved')).count(),
            'pending': apply_date_filters(OrganizationDocument.objects.filter(status='pending')).count(),
            'rejected': apply_date_filters(OrganizationDocument.objects.filter(status='rejected')).count(),
        }

        # Notifications
        notifications_total = apply_date_filters(Notification.objects.all()).count()

        # Support Requests
        support_total = apply_date_filters(HelpSupport.objects.all()).count()
        support_by_status = {
            'pending': apply_date_filters(HelpSupport.objects.filter(status=HelpSupport.Status.PENDING)).count(),
            'closed': apply_date_filters(HelpSupport.objects.filter(status=HelpSupport.Status.CLOSED)).count(),
        }
        support_by_type = {
            'system': apply_date_filters(HelpSupport.objects.filter(type=HelpSupport.SupportType.SYSTEM)).count(),
        }

        # User Application Tracking
        applications_total = apply_date_filters(UserApplicationTracking.objects.all()).count()


        stats = {
            'users': {
                'total': users_total,
                'active': users_active,
                'by_role': users_by_role,
            },
            'organizations': {
                'total': org_total,
                'verified': org_verified,
                'active': org_active,
                'blocked': org_blocked,
            },
            'announcements': {
                'total': ann_total,
                'by_status': ann_by_status,
            },
            'categories': {
                'total': categories_total,
            },
            'favorites': {
                'total': favorites_total,
            },
            'documents': {
                'total': docs_total,
                'by_status': docs_by_status,
            },
            'notifications': {
                'total': notifications_total,
            },
            'support_requests': {
                'total': support_total,
                'by_status': support_by_status,
                'by_type': support_by_type,
            },
            'applications': {
                'total': applications_total,
            },
        }

        applied_filters = {
            'start_date': start_date_str if start_date_str else None,
            'end_date': end_date_str if end_date_str else None,
        }
        return Response({'success': True, 'filters': applied_filters, 'data': stats}, status=status.HTTP_200_OK)

class AdminTimeSeriesStatisticsAPIView(APIView):
    """
    Return time-series counts per day or month for a chosen metric.
    Supports preset periods: day, 7days, month, 3months, 6months, year.
    Supported metrics: users, announcements, organizations, support.
    """
    permission_classes = [IsAuthenticated, IsAdminRole]

    def get(self, request):
        metric = request.query_params.get('metric')
        period = request.query_params.get('period')  # day | 7days | month | 3months | 6months | year

        allowed_metrics = {'users', 'announcements', 'organizations', 'support'}
        allowed_periods = {'day', '7days', 'month', '3months', '6months', 'year'}

        if metric not in allowed_metrics or period not in allowed_periods:
            return Response({
                'success': False,
                'message': 'Invalid metric or period',
                'errors': {
                    'metric': f"must be one of {sorted(list(allowed_metrics))}",
                    'period': f"must be one of {sorted(list(allowed_periods))}",
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()

        def start_of_day(dt):
            return dt.replace(hour=0, minute=0, second=0, microsecond=0)

        def end_of_day(dt):
            return dt.replace(hour=23, minute=59, second=59, microsecond=999999)

        def first_day_of_month(dt):
            return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        def add_months(dt, months):
            # Add (or subtract if negative) months to a datetime, preserving year rollover
            y = dt.year
            m = dt.month
            total = y * 12 + (m - 1) + months
            new_y = total // 12
            new_m = total % 12 + 1
            # Clamp day to 1 for first day-of-month contexts
            return dt.replace(year=new_y, month=new_m, day=1)

        # Determine interval and range based on preset period
        if period in {'day', '7days'}:
            interval = 'day'
            days_back = 1 if period == 'day' else 7
            start_dt = start_of_day(now - timezone.timedelta(days=days_back - 1))
            end_dt = end_of_day(now)
        else:
            interval = 'month'
            months_back_map = {
                'month': 1,
                '3months': 3,
                '6months': 6,
                'year': 12,
            }
            if period == 'month':
                # Use the previous calendar month (last month from today)
                start_dt = first_day_of_month(add_months(now, -1))
                end_month_start = start_dt
                end_dt = end_of_day(add_months(end_month_start, 1) - timezone.timedelta(days=1))
            else:
                months_back = months_back_map[period]
                # Range from first day of the month N-1 months ago up to end of current month
                start_dt = first_day_of_month(add_months(now, -(months_back - 1)))
                # End at end of current month
                end_month_start = first_day_of_month(now)
                end_dt = end_of_day(add_months(end_month_start, 1) - timezone.timedelta(days=1))

        # Select model based on metric
        if metric == 'users':
            model = User
        elif metric == 'announcements':
            model = Announcement
        elif metric == 'organizations':
            model = Organization
        elif metric == 'support':
            model = HelpSupport

        qs = model.objects.filter(created_at__gte=start_dt, created_at__lte=end_dt)

        if interval == 'day':
            aggregated = qs.annotate(bucket=TruncDay('created_at')).values('bucket').annotate(count=Count('id')).order_by('bucket')
        else:
            # For single-month, 3-month, and 6-month views, aggregate at day-level to enable 3-day/2-week/3-week buckets
            if period in {'month', '3months', '6months'}:
                aggregated = qs.annotate(bucket=TruncDay('created_at')).values('bucket').annotate(count=Count('id')).order_by('bucket')
            else:
                aggregated = qs.annotate(bucket=TruncMonth('created_at')).values('bucket').annotate(count=Count('id')).order_by('bucket')

        # Map existing buckets to counts
        bucket_counts = {item['bucket']: item['count'] for item in aggregated}

        # Generate complete bucket sequence and fill zeros
        buckets = []
        total = 0
        if interval == 'day':
            cur = start_of_day(start_dt)
            while cur <= end_dt:
                key = start_of_day(cur)
                count = bucket_counts.get(key, 0)
                buckets.append({'date': key.date().isoformat(), 'count': count})
                total += count
                cur = cur + timezone.timedelta(days=1)
        else:  # month
            if period == 'month':
                # Build 3-day buckets across the selected month range
                cur = start_of_day(start_dt)
                while cur <= end_dt:
                    b_end = cur + timezone.timedelta(days=2)
                    if b_end > end_dt:
                        b_end = end_dt
                    # Sum daily counts within this 3-day window
                    b_cur = cur
                    b_count = 0
                    while b_cur <= b_end:
                        key = start_of_day(b_cur)
                        b_count += bucket_counts.get(key, 0)
                        b_cur = b_cur + timezone.timedelta(days=1)
                    buckets.append({'date': cur.date().isoformat(), 'count': b_count})
                    total += b_count
                    cur = cur + timezone.timedelta(days=3)
            elif period == '3months':
                # Build 2-week buckets across the selected 3-month range
                cur = start_of_day(start_dt)
                while cur <= end_dt:
                    b_end = cur + timezone.timedelta(days=13)
                    if b_end > end_dt:
                        b_end = end_dt
                    # Sum daily counts within this 14-day window
                    b_cur = cur
                    b_count = 0
                    while b_cur <= b_end:
                        key = start_of_day(b_cur)
                        b_count += bucket_counts.get(key, 0)
                        b_cur = b_cur + timezone.timedelta(days=1)
                    buckets.append({'date': cur.date().isoformat(), 'count': b_count})
                    total += b_count
                    cur = cur + timezone.timedelta(days=14)
            elif period == '6months':
                # Build 3-week buckets across the selected 6-month range
                cur = start_of_day(start_dt)
                while cur <= end_dt:
                    b_end = cur + timezone.timedelta(days=20)
                    if b_end > end_dt:
                        b_end = end_dt
                    # Sum daily counts within this 21-day window
                    b_cur = cur
                    b_count = 0
                    while b_cur <= b_end:
                        key = start_of_day(b_cur)
                        b_count += bucket_counts.get(key, 0)
                        b_cur = b_cur + timezone.timedelta(days=1)
                    buckets.append({'date': cur.date().isoformat(), 'count': b_count})
                    total += b_count
                    cur = cur + timezone.timedelta(days=21)
            else:
                # Default monthly buckets for 6-month and year periods
                cur = first_day_of_month(start_dt)
                end_month = first_day_of_month(end_dt)
                while cur <= end_month:
                    key = first_day_of_month(cur)
                    count = bucket_counts.get(key, 0)
                    buckets.append({'date': key.strftime('%Y-%m'), 'count': count})
                    total += count
                    cur = add_months(cur, 1)

        applied_filters = {
            'metric': metric,
            'period': period,
            'interval': interval,
            'start_date': start_dt.date().isoformat(),
            'end_date': end_dt.date().isoformat(),
        }

        return Response({'success': True, 'filters': applied_filters, 'data': {'buckets': buckets, 'total': total}}, status=status.HTTP_200_OK)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsUserRole])
def create_support_request(request):
    serializer = HelpSupportCreateSerializer(data=request.data)
    if serializer.is_valid():
        support_request = serializer.save(user=request.user)
        response_serializer = HelpSupportSerializer(support_request)

        from api.utils.notification_utils import NotificationManager
        notification_manager = NotificationManager(request)
        
        created_notification = None
        if support_request.type in [HelpSupport.SupportType.SYSTEM, HelpSupport.SupportType.OTHER]:
            # Send notification and email to user
            created_notification = notification_manager.notify_support_received(support_request)

        # إرسال إشعار بريد إلكتروني للمديرين عن طلب الدعم الجديد
        try:
            from api.services.email_service import EmailService
            email_service = EmailService(request)
            
            admin_users = User.objects.filter(role=User.Role.ADMIN)
            if admin_users.exists():
                admin_emails = [admin.email for admin in admin_users if admin.email]
                if admin_emails:
                    email_service.send_admin_support_notification(
                        support_request=support_request,
                        admin_emails=admin_emails,
                        fail_silently=True
                    )
        except Exception as e:
            # لا نريد أن يفشل إنشاء طلب الدعم بسبب مشكلة في الإيميل
            print(f"Failed to send admin notification email for support request {support_request.id}: {str(e)}")

        return Response({
            'success': True,
            'message': 'Support request sent successfully',
            'data': response_serializer.data,
            'notification': NotificationDetailSerializer(created_notification).data if created_notification else None
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'success': False,
        'message': 'Invalid data provided',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsUserRole])
def get_user_support_requests(request):
    request_type = request.query_params.get('type')
    queryset = HelpSupport.objects.filter(user=request.user)
    if request_type:
        queryset = queryset.filter(type=request_type)
    queryset = queryset.order_by('-created_at')
    serializer = HelpSupportSerializer(queryset, many=True)
    return Response({'success': True, 'data': serializer.data}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsUserRole])
def get_support_request_detail(request, pk):
    support_request = get_object_or_404(HelpSupport, pk=pk, user=request.user)
    serializer = HelpSupportSerializer(support_request)  
    return Response({'success': True, 'data': serializer.data}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAdminRole])  
def admin_reply_request(request, pk):
    """
    Allows the admin to reply to a support request that is NOT of type 'organization'.
    Sends the reply to the user who created the request.
    """
    # جلب الطلب
    support_request = get_object_or_404(
        HelpSupport,
        pk=pk
    )

    # التحقق من وجود نص الرد
    reply_text = request.data.get('reply')
    if not reply_text:
        return Response({
            "success": False,
            "message": "Reply text is required."
        }, status=400)

    support_request.reply = reply_text
    support_request.status = HelpSupport.Status.CLOSED  # ← تغيير الحالة
    support_request.save()

    # Create in-app notification and send email
    from api.utils.notification_utils import NotificationManager
    notification_manager = NotificationManager(request)
    created_notification = notification_manager.notify_support_reply(support_request, reply_text)

    return Response({
        "success": True,
        "message": "Your reply has been sent to the user successfully and the request is now closed.",
        "notification": NotificationDetailSerializer(created_notification).data
    }, status=200)

class HelpSupportListView(generics.ListAPIView):
    """
    Admin-only view to list and filter help/support requests.
    """
    serializer_class = HelpSupportSerializer
    permission_classes = [IsAdminOnly]

    def get_queryset(self):
        allowed_types = [HelpSupport.SupportType.SYSTEM, HelpSupport.SupportType.OTHER]
        allowed_statuses = [
            HelpSupport.Status.PENDING,
            HelpSupport.Status.CLOSED,
        ]

        queryset = HelpSupport.objects.filter(type__in=allowed_types).select_related("user")

        status_param = self.request.query_params.get("status")
        type_param = self.request.query_params.get("type")

        if status_param:
            queryset = queryset.filter(status=status_param)

        if type_param:
            queryset = queryset.filter(type=type_param)

        return queryset.order_by("-created_at")

    def list(self, request, *args, **kwargs):
        allowed_types = [HelpSupport.SupportType.SYSTEM, HelpSupport.SupportType.OTHER]
        allowed_statuses = [
            HelpSupport.Status.PENDING,
            HelpSupport.Status.CLOSED,
        ]

        type_param = request.query_params.get("type")
        status_param = request.query_params.get("status")

        if type_param and type_param not in allowed_types:
            return Response(
                {
                    "detail": "Invalid type",
                    "allowed_types": allowed_types,
                },
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        if status_param and status_param not in allowed_statuses:
            return Response(
                {
                    "detail": "Invalid status",
                    "allowed_statuses": allowed_statuses,
                },
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        return super().list(request, *args, **kwargs)

@api_view(['GET'])
@permission_classes([IsAdminRole])
def admin_support_request_detail(request, pk):
    """
    Admin-only endpoint to view details of any support request.
    """
    # جلب الطلب
    support_request = get_object_or_404(HelpSupport, pk=pk)

    # Serialize and return
    serializer = HelpSupportAdminSerializer(support_request)
    return Response({
        "success": True,
        "message": "Support request details retrieved successfully.",
        "data": serializer.data
    }, status=200)

@api_view(['GET'])
@permission_classes([IsAdminRole])
def help_support_range_search(request):
    """
    Admin-only endpoint to search support requests by date range.
    Example:
    /api/admin/help-support/search/?start_date=2025-09-01&end_date=2025-09-06
    """
    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")

    if not start_date or not end_date:
        return Response({
            "success": False,
            "message": "Both 'start_date' and 'end_date' parameters are required (YYYY-MM-DD)."
        }, status=status.HTTP_400_BAD_REQUEST)

    start_date = parse_date(start_date)
    end_date = parse_date(end_date)

    if not start_date or not end_date:
        return Response({
            "success": False,
            "message": "Invalid date format. Use YYYY-MM-DD."
        }, status=status.HTTP_400_BAD_REQUEST)

    if start_date > end_date:
        return Response({
            "success": False,
            "message": "'start_date' cannot be greater than 'end_date'."
        }, status=status.HTTP_400_BAD_REQUEST)

    requests_qs = HelpSupport.objects.filter(
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).order_by("-created_at")

    if not requests_qs.exists():
        return Response({
            "success": True,
            "count": 0,
            "message": f"No support requests found between {start_date} and {end_date}.",
            "data": []
        }, status=status.HTTP_200_OK)

    serializer = HelpSupportAdminSerializer(requests_qs, many=True)
    return Response({
        "success": True,
        "count": requests_qs.count(),
        "message": f"Support requests between {start_date} and {end_date}.",
        "data": serializer.data
    }, status=200)

class OrganizationVerificationAPIView(generics.UpdateAPIView):
    queryset = Organization.objects.all()
    serializer_class = OrganizationVerificationSerializer
    permission_classes = [IsAdminOnly]  

    def update(self, request, *args, **kwargs):
        organization = self.get_object()
        serializer = self.get_serializer(organization, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "message": "Organization verification status updated successfully",
            "organization": serializer.data
        }, status=status.HTTP_200_OK)
    
class OrganizationDocumentCreateView(generics.CreateAPIView):

    serializer_class = OrganizationDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save()

class OrganizationDocumentApproveRejectView(generics.UpdateAPIView):
    permission_classes = [IsAdminOnly]
    queryset = OrganizationDocument.objects.all()
    lookup_field = 'id'  # أو أي identifier

    def patch(self, request, *args, **kwargs):
        doc = self.get_object()
        action = request.data.get('action')  # "approve" أو "reject"
        reason = request.data.get('rejection_reason', '')

        if action == 'approve':
            doc.status = 'approved'
            doc.organization.verified = True
            doc.organization.save()
        elif action == 'reject':
            doc.status = 'rejected'
            doc.organization.verified = False
            doc.organization.save()
        else:
            return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

        doc.rejection_reason = reason
        doc.save()
        return Response({"status": doc.status})

@api_view(['GET'])
@permission_classes([IsAdminOnly])  
def list_all_documents(request):
    status_filter = request.GET.get('status') 

    documents = OrganizationDocument.objects.all().order_by('-created_at')

    if status_filter in ['pending', 'approved', 'rejected']:
        documents = documents.filter(status=status_filter)

    serializer = OrganizationDocumentSerializer(documents, many=True)
    return Response({
        'success': True,
        'count': documents.count(),
        'data': serializer.data
    })

class OrganizationDocumentDetailAPIView(generics.RetrieveAPIView):
    """
    Retrieve the details of a specific organization document.
    Only admin can access this endpoint.
    """
    queryset = OrganizationDocument.objects.all()
    serializer_class = OrganizationDocumentSerializer
    permission_classes = [IsAdminOnly]  

    def get_object(self):
        obj = super().get_object()
        return obj

class OrganizationListAPIView(generics.ListAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # منع المستخدمين من نوع "organization"
        if self.request.user.role == "organization":
            return Organization.objects.none()  # ترجع قائمة فارغة
        return Organization.objects.filter(is_active=True)

    def list(self, request, *args, **kwargs):
        if request.user.role == "organization":
            return Response(
                {"success": False, "message": "Organization users cannot access this endpoint."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().list(request, *args, **kwargs)
    
class OrganizationDetailAPIView(generics.RetrieveAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]  
    queryset = Organization.objects.all()
    lookup_field = 'id'

class VerifiedOrganizationListAPIView(generics.ListAPIView):
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == User.Role.ORGANIZATION:
            return Organization.objects.none()  
        
        return Organization.objects.filter(verified=True, is_active=True)

    def list(self, request, *args, **kwargs):
        if request.user.role == User.Role.ORGANIZATION:
            return Response(
                {"success": False, "message": "Organizations cannot access this endpoint."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().list(request, *args, **kwargs)

class SendNotificationAllUsersView(APIView):
    permission_classes = [IsAdminOnly] 

    def post(self, request):
        serializer = NotificationSerializer(data=request.data)
        if serializer.is_valid():
            title = serializer.validated_data['title']
            message = serializer.validated_data['message']

            users = User.objects.filter(role=User.Role.USER)
            
            # Use NotificationManager to handle both notifications and emails
            from api.utils.notification_utils import NotificationManager
            notification_manager = NotificationManager(request)
            
            notification_manager.notify_users_bulk(
                users=list(users),
                title=title,
                message=message,
                email=True,
                cta_url=None,
                cta_label=None
            )

            return Response({"detail": f"Notification sent to {users.count()} users."}, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class SendNotificationToOrganizationsView(APIView):
    permission_classes = [IsAdminOnly] 

    def post(self, request):
        serializer = NotificationSerializer(data=request.data)
        if serializer.is_valid():
            title = serializer.validated_data['title']
            message = serializer.validated_data['message']

            organizations = User.objects.filter(role=User.Role.ORGANIZATION)
            
            # Use NotificationManager to handle both notifications and emails
            from api.utils.notification_utils import NotificationManager
            notification_manager = NotificationManager(request)
            
            notification_manager.notify_users_bulk(
                users=list(organizations),
                title=title,
                message=message,
                email=True,
                cta_url=None,
                cta_label=None
            )

            return Response({"detail": f"Notification sent to {organizations.count()} organizations."}, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class UserNotificationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        notifications = Notification.objects.filter(user=user).order_by('-created_at')

        serializer = NotificationDetailSerializer(notifications, many=True)

        if not notifications.exists():
            return Response(
                {
                    "detail": "Your notifications list is empty.",
                    "notifications": []
                },
                status=200
            )
        
        return Response(
            {
                "detail": "Your notifications list.",
                "notifications": serializer.data
            },
            status=200
        )

        return Response(
            {"notifications": serializer.data},
            status=200
        )

    
class SendNotificationToUserView(APIView):
    permission_classes = [IsAdminOnly]  

    def post(self, request):
        serializer = NotificationToUserSerializer(data=request.data)
        if serializer.is_valid():
            user_id = serializer.validated_data['user_id']
            title = serializer.validated_data['title']
            message = serializer.validated_data['message']

            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            # Use NotificationManager to handle both notification and email
            from api.utils.notification_utils import NotificationManager
            notification_manager = NotificationManager(request)
            
            notification_manager.notify_user(
                user=user,
                title=title,
                message=message,
                email=True,
                cta_url=None,
                cta_label=None
            )

            return Response({"detail": f"Notification sent to {user.name or user.email}"}, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationListSerializer
    permission_classes = [IsAdminOnly]

    def get_queryset(self):
        queryset = Notification.objects.all().order_by('-created_at')
        user_name = self.request.query_params.get('user_name', None)
        title = self.request.query_params.get('title', None)
        user_role = self.request.query_params.get('user_role', None)

        if user_name:
            queryset = queryset.filter(user__name__icontains=user_name)
        if title:
            queryset = queryset.filter(title__icontains=title)
        if user_role:
            queryset = queryset.filter(user__role=user_role)

        return queryset

class NotificationDeleteAllView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request):
        notifications = Notification.objects.filter(user=request.user)
        if not notifications.exists():
            return Response(
                {"detail": "You have no notifications to delete."},
                status=status.HTTP_200_OK
            )

        notifications.delete()
        return Response(
            {"detail": "All your notifications have been deleted."},
            status=status.HTTP_200_OK
        )

class NotificationDeleteView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        title = instance.title  
        self.perform_destroy(instance)
        return Response(
            {"detail": f"Notification '{title}' has been deleted."},
            status=status.HTTP_200_OK
        )
    
class AdminNotificationDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAdminOnly] 
    queryset = Notification.objects.all()  # الأدمن يمكنه الوصول لكل الإشعارات

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        title = instance.title  # عنوان الإشعار
        username = instance.user.name or instance.user.email  # اسم المستلم أو الايميل
        self.perform_destroy(instance)
        return Response(
            {"detail": f"Notification '{title}' sent to '{username}' has been deleted by admin."},
            status=status.HTTP_200_OK
        )
    
class DeleteUserView(generics.DestroyAPIView):
    permission_classes = [IsAdminOnly]

    def delete(self, request, user_id):
        user = get_object_or_404(User, id=user_id, role='user')  # فقط اليوزر العادي
        user.delete()
        return Response({"detail": "User deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
    
class DeleteOrganizationView(generics.DestroyAPIView):
    permission_classes = [IsAdminOnly]

    def delete(self, request, org_id):
        org = get_object_or_404(Organization, id=org_id)

        user = org.user  

        org.delete()

        if user:
            user.delete()

        return Response({"detail": "Organization deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
    
class OrganizationListView(generics.ListAPIView):
    queryset = Organization.objects.all().order_by('-created_at')
    serializer_class = OrganizationAdminSerializer
    permission_classes = [IsAdminOnly]

class OrganizationActiveFilterAPIView(generics.ListAPIView):
    """
    Generic API view to list organizations with optional active/inactive filtering
    """
    serializer_class = OrganizationAdminSerializer
    queryset = Organization.objects.all()
    permission_classes = [IsAdminOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        # فلترة حسب is_active من query params
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            if is_active.lower() == 'true':
                queryset = queryset.filter(is_active=True)
            elif is_active.lower() == 'false':
                queryset = queryset.filter(is_active=False)
        return queryset


# =========================
# 🌐 Language Switching
# =========================

@api_view(['POST'])
@permission_classes([AllowAny])
def set_language(request):
    """
    API endpoint to set the user's language preference.
    Supports both session-based and user profile-based language setting.
    """
    language_code = request.data.get('language', 'en')
    
    # Validate language code
    if language_code not in ['ar', 'en']:
        return JsonResponse({
            'error': _('Invalid language code. Supported languages: ar, en')
        }, status=400)
    
    # Set language in session
    request.session['django_language'] = language_code
    
    # If user is authenticated, save to user profile
    if request.user.is_authenticated:
        try:
            request.user.preferred_language = language_code
            request.user.save(update_fields=['preferred_language'])
        except Exception as e:
            # Handle case where User model doesn't have preferred_language field
            pass
    
    # Activate the language for this request
    translation.activate(language_code)
    
    return JsonResponse({
        'success': True,
        'language': language_code,
        'message': _('Language preference updated successfully')
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_current_language(request):
    """
    API endpoint to get the current active language.
    """
    current_language = translation.get_language() or 'en'
    
    return JsonResponse({
        'current_language': current_language,
        'available_languages': [
            {'code': 'en', 'name': 'English'},
            {'code': 'ar', 'name': 'Arabic'}
        ]
    })
