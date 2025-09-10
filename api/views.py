from rest_framework import status, generics, viewsets, filters
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from rest_framework import permissions
from django.core.mail import send_mail
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from django.shortcuts import get_object_or_404
from django.http import Http404
from rest_framework.exceptions import PermissionDenied
import os
from django.utils.dateparse import parse_date


from .models import (
    User, Organization,
    Announcement,
    UserFavorite,
    HelpSupport,
    OrganizationDocument,
    AnnouncementEditRequest,
    UserApplicationTracking,
    Notification,
)
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from .models import User, Organization, Announcement, AnnouncementCategory
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
    AnnouncementEditRequestCreateSerializer,
    NotificationSerializer,
    AnnouncementEditRequestListSerializer,
    AnnouncementEditRequestDetailSerializer,
    AnnouncementEditRequestApprovalSerializer,
    OrganizationToggleActiveSerializer,
    LogoutSerializer,
    UserApplicationTrackingSerializer,
    HelpSupportAdminSerializer,
    HelpSupportSerializer,
    HelpSupportCreateSerializer,
    OrganizationDocumentSerializer,
    OrganizationSerializer,
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
            return request.build_absolute_uri(user.profile_image.url)
        else:
            # File doesn't exist, use default
            default_image_path = 'defaults/user_default.png'
            return request.build_absolute_uri(settings.MEDIA_URL + default_image_path)
    else:
        # No profile image set, use default
        default_image_path = 'defaults/user_default.png'
        return request.build_absolute_uri(settings.MEDIA_URL + default_image_path)

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

        # Email content
        message = f"""
Hello {user.name or user.email},

You requested to reset your password.

Click the link below to reset your password:
{reset_url}

Or copy this link into your browser.

Note: This link is valid for a limited time only.
"""

        send_mail(
            subject="Password Reset",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response({
            "success": True,
            "message": "Password reset link sent successfully",
            "data": {
                "email": user.email
            }
        }, status=status.HTTP_200_OK)


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

            # تحديث بيانات User الشخصية (بدون profile_image)
            for field in ['name', 'email', 'phone']:
                if field in request.data:
                    setattr(user, field, request.data[field])
            user.save()

            # تحديث بيانات المؤسسة (description, website, location, profile_image)
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
        
        if user.is_authenticated and user.role == User.Role.ADMIN:
            # Admin can see all announcements in all actions
            return Announcement.objects.all()
        elif self.action in ['list', 'retrieve']:
            # Public view - only approved announcements for non-admin users
            return Announcement.objects.filter(status=Announcement.Status.APPROVED)
        elif user.is_authenticated:
            if user.role == User.Role.ORGANIZATION:
                # Organization can see their own announcements
                return Announcement.objects.filter(created_by=user)
            else:
                # Regular users can only see approved announcements
                return Announcement.objects.filter(status=Announcement.Status.APPROVED)
        else:
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
        
        queryset = self.filter_queryset(self.get_queryset())
        
        # If filtering by ID and no results found, return error
        if id_filter and not queryset.exists():
            return Response({
                'success': False,
                'message': f'No announcement found with ID: {id_filter}'
            }, status=status.HTTP_404_NOT_FOUND)
            
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
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_200_OK)
        except Http404:
            return Response({
                'success': False,
                'message': f'No announcement found with ID: {kwargs.get("pk")}'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['patch'], url_path='approve')
    def approve(self, request, pk=None):
        """Admin action to approve/reject announcements"""
        announcement = self.get_object()
        serializer = self.get_serializer(announcement, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            
            # Send notification to announcement creator
            status_text = "approved" if announcement.status == Announcement.Status.APPROVED else "rejected"
            # Here you can add notification logic
            
            return Response({
                'success': True,
                'message': f'Announcement {status_text} successfully',
                'data': AnnouncementAdminSerializer(announcement).data
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
        """Get current user's announcements"""
        if not request.user.is_authenticated:
            return Response({
                'success': False,
                'message': 'Authentication required'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        announcements = Announcement.objects.filter(created_by=request.user)
        serializer = AnnouncementListSerializer(announcements, many=True, context={'request': request})
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        """Override to set created_by field"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'], url_path='track-application', permission_classes=[IsAuthenticated])
    def track_application(self, request, pk=None):
        """
        Track user application status and set reminders
        POST /api/announcements/{id}/track-application/
        
        Expected payload:
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
        
        # Check if tracking already exists for this user and announcement
        tracking, created = UserApplicationTracking.objects.get_or_create(
            user=request.user,
            announcement=announcement,
            defaults={
                'status': request.data.get('status', 'not applied'),
                'notes': request.data.get('notes', ''),
                'reminder_date': request.data.get('reminder_date')
            }
        )
        
        if not created:
            # Update existing tracking
            if 'status' in request.data:
                tracking.status = request.data.get('status')
            if 'notes' in request.data:
                tracking.notes = request.data.get('notes')
            if 'reminder_date' in request.data:
                tracking.reminder_date = request.data.get('reminder_date')
            tracking.save()
        
        serializer = UserApplicationTrackingSerializer(tracking)
        return Response({
            'success': True,
            'message': 'Application tracking updated successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['delete'], url_path='track-application', permission_classes=[IsAuthenticated])
    def remove_application_tracking(self, request, pk=None):
        """
        Remove user application tracking
        DELETE /api/announcements/{id}/track-application/
        """
        # Check if user has 'user' role
        if request.user.role != User.Role.USER:
            return Response({
                'success': False,
                'message': 'Only users with user role can remove application tracking'
            }, status=status.HTTP_403_FORBIDDEN)
        
        announcement = self.get_object()
        
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
        serializer = UserApplicationTrackingSerializer(applications, many=True)
        
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
    
    def _handle_approved_announcement_edit(self, announcement, request_data):
        """Handle edit request for approved announcements"""
        # Create edit request instead of direct update
        edit_request_data = {
            'original_announcement': announcement.id,
            'proposed_title': request_data.get('title', announcement.title),
            'proposed_description': request_data.get('description', announcement.description),
            'proposed_start_date': request_data.get('start_date', announcement.start_date),
            'proposed_end_date': request_data.get('end_date', announcement.end_date),
            'proposed_url': request_data.get('url', announcement.url),
            'proposed_category': request_data.get('category', announcement.category.id if announcement.category else None)
        }
        
        serializer = AnnouncementEditRequestCreateSerializer(
            data=edit_request_data, 
            context={'request': self.request}
        )
        
        if serializer.is_valid():
            edit_request = serializer.save(requested_by=self.request.user)
            response_serializer = AnnouncementEditRequestDetailSerializer(edit_request)
            
            return Response({
                'success': True,
                'message': 'Edit request created successfully. Waiting for admin approval.',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'message': 'Edit request validation failed',
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
            updated_announcement = serializer.save()
            response_serializer = AnnouncementDetailSerializer(updated_announcement)
            
            return Response({
                'success': True,
                'message': 'Announcement approved successfully',
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
            return self._handle_approved_announcement_edit(announcement, request.data)
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
            return self._handle_approved_announcement_edit(announcement, request.data)
        else:
            # Direct update for unapproved announcements or admin updates
            return self._handle_direct_update(announcement, request.data, partial=True)
        

class AnnouncementEditRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing announcement edit requests
    - Organizations can view their edit requests
    - Admins can view all edit requests and approve/reject them
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter edit requests based on user role"""
        user = self.request.user
        
        if user.role == User.Role.ADMIN:
            # Admins can see all edit requests
            return AnnouncementEditRequest.objects.all()
        elif user.role == User.Role.ORGANIZATION:
            # Organizations can only see their own edit requests
            return AnnouncementEditRequest.objects.filter(requested_by=user)
        else:
            # Regular users cannot access edit requests
            return AnnouncementEditRequest.objects.none()
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return AnnouncementEditRequestCreateSerializer
        elif self.action in ['list']:
            return AnnouncementEditRequestListSerializer
        elif self.action == 'approve_reject':
            return AnnouncementEditRequestApprovalSerializer
        else:
            return AnnouncementEditRequestDetailSerializer
    
    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['create', 'list', 'retrieve']:
            permission_classes = [IsAuthenticated]
        elif self.action in ['approve_reject']:
            permission_classes = [IsAdminOnly]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    def create(self, request):
        """Create new edit request (organizations only)"""
        if request.user.role != User.Role.ORGANIZATION:
            return Response({
                'success': False,
                'message': 'Only organizations can create edit requests'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            edit_request = serializer.save(requested_by=request.user)
            response_serializer = AnnouncementEditRequestDetailSerializer(edit_request)
            
            return Response({
                'success': True,
                'message': 'Edit request created successfully',
                'data': response_serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'detail': 'Validation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['patch'], url_path='approve-reject')
    def approve_reject(self, request, pk=None):
        """Admin action to approve or reject edit requests"""
        edit_request = self.get_object()
        
        if edit_request.status != AnnouncementEditRequest.Status.PENDING:
            return Response({
                'success': False,
                'message': 'Edit request has already been reviewed'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(edit_request, data=request.data, partial=True)
        
        if serializer.is_valid():
            updated_edit_request = serializer.save()
            response_serializer = AnnouncementEditRequestDetailSerializer(updated_edit_request)
            
            status_text = "approved" if updated_edit_request.status == AnnouncementEditRequest.Status.APPROVED else "rejected"
            
            return Response({
                'success': True,
                'message': f'Edit request {status_text} successfully',
                'data': response_serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'detail': 'Validation failed',
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'], url_path='pending')
    def pending_edit_requests(self, request):
        """Admin action to get pending edit requests"""
        if request.user.role != User.Role.ADMIN:
            return Response({
                'success': False,
                'message': 'Only admins can access pending edit requests'
            }, status=status.HTTP_403_FORBIDDEN)
        
        pending = AnnouncementEditRequest.objects.filter(status=AnnouncementEditRequest.Status.PENDING)
        serializer = AnnouncementEditRequestListSerializer(pending, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'message': 'Pending edit requests retrieved successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)


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
                return Response({
                    'success': False,
                    'message': 'No organization found for this user'
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Error retrieving organization information'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = AnnouncementCreateSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            # Set the creator and organization
            announcement = serializer.save(
                created_by=request.user,
                organization=organization
            )
            
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
    permission_classes = [IsAdminUser]

class ToggleBlockUserAPIView(APIView):
    permission_classes = [permissions.IsAdminUser]  # فقط admins

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
    permission_classes = [permissions.IsAdminUser] 

    def get_queryset(self):
        return User.objects.all().order_by('-created_at')
    
class UserDetailAPIView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]  
    queryset = User.objects.all()
    lookup_field = 'id'

class UserSearchAPIView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]  # Admin فقط

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
    
@api_view(['POST'])
@permission_classes([IsAuthenticated, IsUserRole])
def create_support_request(request):
    serializer = HelpSupportCreateSerializer(data=request.data)
    if serializer.is_valid():
        support_request = serializer.save(user=request.user)
        response_serializer = HelpSupportSerializer(support_request)

        # Check if the request is of type Organization Complaint and has a target organization
        if support_request.type == HelpSupport.SupportType.ORGANIZATION and support_request.target_org:
            subject = "Your support request has been received"
            message = f"Hello {support_request.user.name},\n\n" \
                      f"Your support request titled '{support_request.title}' has been successfully received " \
                      f"and will be forwarded to the relevant authorities. Please wait for their response.\n\n" \
                      f"Thank you."
            recipient_list = [support_request.user.email]
            
            try:
                send_mail(subject, message, 'no-reply@yourplatform.com', recipient_list)
            except Exception as e:
                # يمكنك فقط تسجيل الخطأ دون منع الاستجابة الناجحة
                print(f"Failed to send email: {str(e)}")

        return Response({
            'success': True,
            'message': 'Support request sent successfully',
            'data': response_serializer.data
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
def send_request_to_organization(request, pk):
    """
    Mark the support request as sent to the target organization.
    """
    support_request = get_object_or_404(HelpSupport, pk=pk)

    if support_request.type != HelpSupport.SupportType.ORGANIZATION:
        return Response({
            "success": False,
            "message": "This request is not of type 'Organization Complaint'."
        }, status=status.HTTP_400_BAD_REQUEST)

    if not support_request.target_org:
        return Response({
            "success": False,
            "message": "An organization request must have a target organization (target_org)."
        }, status=status.HTTP_400_BAD_REQUEST)

    # تغيير حالة الطلب
    support_request.status = HelpSupport.Status.SENT
    support_request.save()

    org_name = support_request.target_org.user.name  # اسم المؤسسة من جدول User المرتبط
    return Response({
        "success": True,
        "message": f"The complaint has been sent to the organization: {org_name}."
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsOrganizationRole])  # صلاحية المؤسسة فقط
def organization_reply_request(request, pk):
    """
    Allows the organization to respond to a support request.
    Sends the reply to the user who created the request.
    """
    # جلب المؤسسة الحالية
    try:
        organization = Organization.objects.get(user=request.user)
    except Organization.DoesNotExist:
        return Response({
            "success": False,
            "message": "This user is not linked to any organization."
        }, status=403)

    # جلب الطلب الذي يكون target_org هو المؤسسة الحالية وحالته SENT
    support_request = get_object_or_404(
        HelpSupport,
        pk=pk,
        target_org=organization,
        status=HelpSupport.Status.SENT
    )

    # البيانات المرسلة
    reply_text = request.data.get('reply')
    if not reply_text:
        return Response({
            "success": False,
            "message": "Reply text is required."
        }, status=400)

    # حفظ الرد وتغيير الحالة إلى closed
    support_request.reply = reply_text
    support_request.status = HelpSupport.Status.CLOSED  # ← تحديث الحالة
    support_request.save()

    # إرسال إيميل للمستخدم الذي قدم الطلب
    subject = f"Response to your support request: {support_request.title}"
    message = f"Hello {support_request.user.name},\n\n" \
              f"The organization {organization.user.name} has responded to your support request:\n\n" \
              f"{reply_text}\n\nThank you."
    recipient_list = [support_request.user.email]

    try:
        send_mail(subject, message, 'no-reply@yourplatform.com', recipient_list)
    except Exception as e:
        return Response({
            "success": False,
            "message": f"Failed to send email: {str(e)}"
        }, status=500)

    return Response({
        "success": True,
        "message": "Your reply has been sent to the user successfully and the request is now closed."
    }, status=200)

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

    # التحقق من نوع الطلب
    if support_request.type == HelpSupport.SupportType.ORGANIZATION:
        return Response({
            "success": False,
            "message": "Admins cannot reply to organization complaints. Use the organization endpoint."
        }, status=400)

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

    # إرسال إيميل للمستخدم الذي قدم الطلب
    subject = f"Response to your support request: {support_request.title}"
    message = f"Hello {support_request.user.name},\n\n" \
              f"The admin has responded to your support request:\n\n" \
              f"{reply_text}\n\nThank you."
    recipient_list = [support_request.user.email]

    try:
        send_mail(subject, message, 'no-reply@yourplatform.com', recipient_list)
    except Exception as e:
        return Response({
            "success": False,
            "message": f"Failed to send email: {str(e)}"
        }, status=500)

    return Response({
        "success": True,
        "message": "Your reply has been sent to the user successfully and the request is now closed."
    }, status=200)


@api_view(['GET'])
@permission_classes([IsOrganizationRole])
def organization_admin_requests(request):
    try:
        organization = Organization.objects.get(user=request.user)
    except Organization.DoesNotExist:
        return Response({
            "success": False,
            "message": "This user is not linked to any organization."
        }, status=403)

    # بداية queryset: كل الطلبات المرتبطة بالمؤسسة
    requests_qs = HelpSupport.objects.filter(target_org=organization)

    # ✅ فلترة حسب الحالة
    status_param = request.query_params.get('status')  # مثال: ?status=SENT,CLOSED
    valid_statuses = [s.value for s in HelpSupport.Status]  # قائمة الحالات الصحيحة

    if status_param:
        status_list = [s.strip().lower() for s in status_param.split(',')]
        # التحقق من صحة القيم
        invalid_status = [s for s in status_list if s not in valid_statuses]
        if invalid_status:
            return Response({
                "success": False,
                "detail": f"Invalid status value(s): {', '.join(invalid_status)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        requests_qs = requests_qs.filter(status__in=status_list)
    else:
        requests_qs = requests_qs.filter(status__in=[HelpSupport.Status.SENT, HelpSupport.Status.CLOSED])

    # ✅ فلترة حسب النوع
    type_param = request.query_params.get('type')  # مثال: ?type=system,organization
    valid_types = [t.value for t in HelpSupport.SupportType]
    if type_param:
        type_list = [t.strip().lower() for t in type_param.split(',')]
        invalid_type = [t for t in type_list if t not in valid_types]
        if invalid_type:
            return Response({
                "success": False,
                "detail": f"Invalid type value(s): {', '.join(invalid_type)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        requests_qs = requests_qs.filter(type__in=type_list)

    requests_qs = requests_qs.order_by('-created_at')

    serializer = HelpSupportAdminSerializer(requests_qs, many=True)
    return Response({
        "success": True,
        "count": requests_qs.count(),
        "message": "Filtered requests sent by admin to your organization.",
        "data": serializer.data
    }, status=200)

class HelpSupportListView(generics.ListAPIView):
    """
    Admin-only view to list and filter help/support requests.
    """
    serializer_class = HelpSupportSerializer
    permission_classes = [IsAdminOnly]

    def get_queryset(self):
        queryset = HelpSupport.objects.all().select_related("user", "target_org__user")

        status_param = self.request.query_params.get("status")
        type_param = self.request.query_params.get("type")

        if status_param:
            queryset = queryset.filter(status=status_param)

        if type_param:
            queryset = queryset.filter(type=type_param)

        return queryset.order_by("-created_at")

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

class OrganizationDocumentCreateView(generics.CreateAPIView):

    serializer_class = OrganizationDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save()

class OrganizationDocumentApproveRejectView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAdminUser]
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
@permission_classes([IsAdminUser])  
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
    permission_classes = [permissions.IsAdminUser]  

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
