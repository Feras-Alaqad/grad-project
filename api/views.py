from rest_framework import status, generics, viewsets, filters
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.core.mail import send_mail
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import (
    User, Organization,
    Announcement, Application,
    UserFavorite
)
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from .models import User, Organization, Announcement, AnnouncementCategory, Application
from .serializers import (
    UserSignupSerializer,
    UserSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
    OrganizationSignupSerializer,
    OrganizationProfileSerializer,
    CustomTokenObtainPairSerializer,
    UserFavoriteSerializer,
    AnnouncementListSerializer,
    AnnouncementDetailSerializer,
    AnnouncementCreateSerializer,
    AnnouncementUpdateSerializer,
    AnnouncementAdminSerializer,
    AnnouncementApprovalSerializer,
    AnnouncementCategorySerializer,
    ApplicationCreateSerializer,
    ApplicationListSerializer,
    ApplicationDetailSerializer,
    ApplicationUpdateSerializer,
    UserApplicationSerializer
)


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
    def post(self, request):
        serializer = UserSignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # إنشاء توكن وريفريش
            refresh = RefreshToken.for_user(user)
            return Response({
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "phone": user.phone
                },
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token)
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OrganizationSignupView(APIView):
    def post(self, request):
        email = request.data.get('email')
        if User.objects.filter(email=email).exists():
            return Response(
                {"error": "This email is already in use."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = OrganizationSignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()  # إنشاء المستخدم والمؤسسة

            # لا يتم إصدار التوكن بعد، لأن الحساب غير مفعل
            return Response(
                {"message": "Your registration request has been received. Please wait for admin approval."},
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class OrganizationAcceptView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, org_id):
        try:
            org = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            return Response({"detail": "Organization not found."}, status=404)

        if org.is_active:
            return Response({"detail": "Organization is already active."}, status=400)

        # تفعيل المؤسسة
        org.is_active = True
        org.is_rejected = False       # إعادة ضبط الرفض
        org.rejection_reason = ''
        org.save()

        # إنشاء التوكن للمستخدم المرتبط
        user = org.user
        refresh = RefreshToken.for_user(user)

        return Response({
            "detail": "Organization activated successfully.",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "phone": user.phone,
                "role": user.role
            },
            "refresh": str(refresh),
            "access": str(refresh.access_token)
        }, status=200)

class OrganizationRejectionView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, org_id):
        reason = request.data.get("reason", "")
        if not reason:
            return Response({"detail": "Rejection reason is required."}, status=400)

        try:
            org = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            return Response({"detail": "Organization not found."}, status=404)

        org.is_rejected = True
        org.rejection_reason = reason
        org.is_active = False
        org.save()

        return Response({"detail": "Organization has been rejected.", "reason": reason}, status=200)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
# views.py
class ForgotPasswordAPIView(generics.GenericAPIView):
    """
    API for requesting password reset
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "No account found with this email."}, status=status.HTTP_404_NOT_FOUND)

        token = default_token_generator.make_token(user)

        # استخدم user.id بدل uidb64
        reset_url = f"https://awn-three.vercel.app/reset-password/register/{user.id}/{token}/"

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
            "message": "Password reset link sent successfully",
            "email": user.email
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
            'message': 'Password reset successful',
            'user_email': user.email
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
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_jwt_token(request):
    """
    تحقق من صحة توكن JWT ويرجع رسالة مناسبة
    """
    token = request.data.get('token')

    if not token:
        return Response({"valid": False, "message": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # التحقق من التوكن
        UntypedToken(token)
        return Response({"valid": True, "message": "Token is valid"}, status=status.HTTP_200_OK)
    except (InvalidToken, TokenError) as e:
        return Response({"valid": False, "message": "Invalid or expired token"}, status=status.HTTP_401_UNAUTHORIZED)
    
class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role == user.Role.ORGANIZATION:
            try:
                organization = Organization.objects.get(user=user)
            except Organization.DoesNotExist:
                return Response({"detail": "Organization profile not found."}, status=404)
            
            serializer = OrganizationProfileSerializer(organization)
            return Response(serializer.data)
        else:
            serializer = UserSerializer(user)
            return Response(serializer.data)
    def put(self, request):
        user = request.user

        forbidden_fields = ['website', 'location', 'description']
        if user.role == user.Role.USER:
            for field in forbidden_fields:
                if field in request.data:
                    return Response(
                        {"detail": "You are a USER, not an ORGANIZATION."},
                        status=403
                    )

        if user.role == user.Role.ORGANIZATION:
            try:
                organization = Organization.objects.get(user=user)
            except Organization.DoesNotExist:
                return Response({"detail": "Organization profile not found."}, status=404)

            serializer = OrganizationProfileSerializer(
                organization, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        
        else:
            serializer = UserSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
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
    filterset_fields = ['category', 'organization', 'status']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'start_date', 'end_date']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        
        if self.action in ['list', 'retrieve']:
            # Public view - only approved announcements
            return Announcement.objects.filter(status=Announcement.Status.APPROVED)
        elif user.is_authenticated:
            if user.role == User.Role.ADMIN:
                # Admin can see all announcements
                return Announcement.objects.all()
            elif user.role == User.Role.ORGANIZATION:
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
            return AnnouncementAdminSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]
        elif self.action == 'create':
            permission_classes = [IsAdminOrOrganization]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsOwnerOrAdmin]
        elif self.action in ['approve', 'pending_announcements']:
            permission_classes = [IsAdminOnly]
        else:
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]

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
                'message': f'Announcement {status_text} successfully',
                'announcement': AnnouncementAdminSerializer(announcement).data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='pending')
    def pending_announcements(self, request):
        """Admin action to get pending announcements"""
        pending = Announcement.objects.filter(status=Announcement.Status.PENDING)
        serializer = AnnouncementAdminSerializer(pending, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='my-announcements')
    def my_announcements(self, request):
        """Get current user's announcements"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        
        announcements = Announcement.objects.filter(created_by=request.user)
        serializer = AnnouncementAdminSerializer(announcements, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        """Override to set created_by field"""
        serializer.save(created_by=self.request.user)


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
            return [IsAdminOrOrganization()]
        return [IsAuthenticated()]
    
    def get(self, request):
        """
        List announcements with filtering and search
        """
        # Base queryset
        if request.user.role == User.Role.ADMIN:
            queryset = Announcement.objects.all()
        else:
            # Regular users see only approved announcements
            queryset = Announcement.objects.filter(status=Announcement.Status.APPROVED)
        
        # Apply filters
        category = request.query_params.get('category')
        organization = request.query_params.get('organization')
        status_filter = request.query_params.get('status')
        search = request.query_params.get('search')
        
        if category:
            queryset = queryset.filter(category_id=category)
        if organization:
            queryset = queryset.filter(organization_id=organization)
        if status_filter and request.user.role == User.Role.ADMIN:
            queryset = queryset.filter(status=status_filter)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(description__icontains=search)
            )
        
        # Order by creation date
        queryset = queryset.order_by('-created_at')
        
        # Serialize data
        serializer = AnnouncementListSerializer(queryset, many=True)
        
        return Response({
            'success': True,
            'count': queryset.count(),
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
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


class ApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing applications to announcements.
    Provides CRUD operations with proper permission handling.
    """
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'announcement', 'announcement__organization']
    search_fields = ['announcement__title', 'announcement__organization__name']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Return applications based on user role and permissions.
        """
        user = self.request.user
        
        if user.is_staff:  # Admin can see all applications
            return Application.objects.all().select_related('user', 'announcement', 'announcement__organization')
        elif hasattr(user, 'organization'):  # Organization can see applications to their announcements
            return Application.objects.filter(
                announcement__organization=user.organization
            ).select_related('user', 'announcement', 'announcement__organization')
        else:  # Regular users can only see their own applications
            return Application.objects.filter(
                user=user
            ).select_related('user', 'announcement', 'announcement__organization')
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action and user role.
        """
        if self.action == 'create':
            return ApplicationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ApplicationUpdateSerializer
        elif self.action == 'list':
            if hasattr(self.request.user, 'organization') or self.request.user.is_staff:
                return ApplicationListSerializer
            else:
                return UserApplicationSerializer
        else:  # retrieve
            return ApplicationDetailSerializer
    
    def get_permissions(self):
        """
        Set permissions based on action.
        """
        if self.action == 'create':
            permission_classes = [IsAuthenticated]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated]  # Will check ownership in perform_update/destroy
        else:
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def perform_create(self, serializer):
        """
        Set the user when creating an application.
        """
        serializer.save(user=self.request.user)
    
    def perform_update(self, serializer):
        """
        Only allow admins and organization owners to update applications.
        """
        application = self.get_object()
        user = self.request.user
        
        # Check if user has permission to update this application
        if not (user.is_staff or 
                (hasattr(user, 'organization') and 
                 application.announcement.organization == user.organization)):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to update this application.")
        
        serializer.save()
    
    def perform_destroy(self, serializer):
        """
        Only allow users to delete their own applications or admins to delete any.
        """
        application = self.get_object()
        user = self.request.user
        
        # Check if user has permission to delete this application
        if not (user.is_staff or application.user == user):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You don't have permission to delete this application.")
        
        application.delete()
    
    @action(detail=False, methods=['get'], url_path='my-applications')
    def my_applications(self, request):
        """
        Get current user's applications.
        """
        applications = Application.objects.filter(
            user=request.user
        ).select_related('announcement', 'announcement__organization')
        
        serializer = UserApplicationSerializer(applications, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=True, methods=['patch'], url_path='approve')
    def approve(self, request, pk=None):
        """
        Approve an application (admin and organization only).
        """
        application = self.get_object()
        user = request.user
        
        # Check permissions
        if not (user.is_staff or 
                (hasattr(user, 'organization') and 
                 application.announcement.organization == user.organization)):
            return Response({
                'success': False,
                'message': 'You do not have permission to approve applications.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        application.status = Application.Status.APPROVED
        application.save()
        
        serializer = ApplicationDetailSerializer(application)
        return Response({
            'success': True,
            'message': 'Application approved successfully',
            'data': serializer.data
        })
    
    @action(detail=True, methods=['patch'], url_path='reject')
    def reject(self, request, pk=None):
        """
        Reject an application (admin and organization only).
        """
        application = self.get_object()
        user = request.user
        
        # Check permissions
        if not (user.is_staff or 
                (hasattr(user, 'organization') and 
                 application.announcement.organization == user.organization)):
            return Response({
                'success': False,
                'message': 'You do not have permission to reject applications.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get admin notes from request
        admin_notes = request.data.get('admin_notes', '')
        
        application.status = Application.Status.REJECTED
        application.admin_notes = admin_notes
        application.save()
        
        serializer = ApplicationDetailSerializer(application)
        return Response({
            'success': True,
            'message': 'Application rejected successfully',
            'data': serializer.data
        })
    
    @action(detail=False, methods=['get'], url_path='pending')
    def pending_applications(self, request):
        """
        Get pending applications (admin and organization only).
        """
        user = request.user
        
        if user.is_staff:
            # Admin can see all pending applications
            applications = Application.objects.filter(
                status=Application.Status.PENDING
            ).select_related('user', 'announcement', 'announcement__organization')
        elif hasattr(user, 'organization'):
            # Organization can see pending applications to their announcements
            applications = Application.objects.filter(
                status=Application.Status.PENDING,
                announcement__organization=user.organization
            ).select_related('user', 'announcement', 'announcement__organization')
        else:
            return Response({
                'success': False,
                'message': 'You do not have permission to view pending applications.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ApplicationListSerializer(applications, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })


class OrganizationSearchView(APIView):
    """
    API endpoint for searching organizations by name.
    Only accessible by admin users. 
    """
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAdminOnly()]
        return super().get_permissions()
    
    def get(self, request):
        """Search organizations by name"""
        search_query = request.query_params.get('q', '').strip()
        
        if not search_query:
            return Response({
                'success': False,
                'message': 'Search query parameter "q" is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Search organizations with case-insensitive name matching
        organizations = Organization.objects.filter(
            name__icontains=search_query
        ).values('id', 'name', 'email')[:10]  # Limit to 10 results
        
        return Response({
            'success': True,
            'message': 'Organizations found',
            'data': list(organizations)
        }, status=status.HTTP_200_OK)


# =========================
# 🔹 Admin Organization Management
# =========================




class UpdateAnnouncementView(APIView):
    """
    Dedicated view for updating announcements
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
    
    def put(self, request, pk):
        """Full update of announcement"""
        announcement = self.get_object(pk)
        
        if not announcement:
            return Response({
                'success': False,
                'message': 'Announcement not found or permission denied'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AnnouncementUpdateSerializer(announcement, data=request.data, context={'request': request})
        
        if serializer.is_valid():
            updated_announcement = serializer.save()
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
    
    def patch(self, request, pk):
        """Partial update of announcement"""
        announcement = self.get_object(pk)
        
        if not announcement:
            return Response({
                'success': False,
                'message': 'Announcement not found or permission denied'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = AnnouncementUpdateSerializer(announcement, data=request.data, partial=True, context={'request': request})
        
        if serializer.is_valid():
            updated_announcement = serializer.save()
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
        
class AddFavoriteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, announcement_id):
        user = request.user
        try:
            announcement = Announcement.objects.get(id=announcement_id)
        except Announcement.DoesNotExist:
            return Response({"detail": "Announcement not found."}, status=status.HTTP_404_NOT_FOUND)

        # التحقق من وجود Application مع is_favorite = True
        try:
            app = Application.objects.get(user=user, announcement=announcement, is_favorite=True)
        except Application.DoesNotExist:
            return Response({"detail": "Cannot add to favorites. Application is not marked as favorite."},
                            status=status.HTTP_400_BAD_REQUEST)

        favorite, created = UserFavorite.objects.get_or_create(user=user, announcement=announcement)
        serializer = UserFavoriteSerializer(favorite)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class RemoveFavoriteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, announcement_id):
        user = request.user
        try:
            favorite = UserFavorite.objects.get(user=user, announcement_id=announcement_id)
        except UserFavorite.DoesNotExist:
            return Response({"detail": "Favorite not found."}, status=status.HTTP_404_NOT_FOUND)

        favorite.delete()
        return Response({"detail": "Announcement removed from favorites."}, status=status.HTTP_200_OK)