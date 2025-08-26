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
from rest_framework_simplejwt.views import TokenObtainPairView
from django.shortcuts import get_object_or_404

from .models import (
    User, Organization,
    Announcement, Application,
    UserFavorite,
    HelpSupport
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
    CustomTokenObtainPairSerializer,
    UserFavoriteSerializer,
    AnnouncementListSerializer,
    AnnouncementDetailSerializer,
    AnnouncementCreateSerializer,
    AnnouncementUpdateSerializer,
    AnnouncementAdminSerializer,
    AnnouncementApprovalSerializer,
    AnnouncementCategorySerializer,
    OrganizationToggleActiveSerializer,
    LogoutSerializer,
    HelpSupportAdminSerializer,
    HelpSupportSerializer,
    HelpSupportCreateSerializer,
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

    def post(self, request, application_id):
        user = request.user

        # التحقق من دور اليوزر
        if user.role != User.Role.USER:
            return Response(
                {"detail": "Only users with role 'user' can add favorites."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            application = Application.objects.get(id=application_id)
        except Application.DoesNotExist:
            return Response({"detail": "Application not found."}, status=status.HTTP_404_NOT_FOUND)

        favorite, created = UserFavorite.objects.get_or_create(
            application=application,
            user=user
        )

        serializer = UserFavoriteSerializer(favorite)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class RemoveFavoriteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, application_id):
        user = request.user

        if user.role != User.Role.USER:
            return Response(
                {"detail": "Only users with role 'user' can remove favorites."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            favorite = UserFavorite.objects.get(application__id=application_id, user=user)
        except UserFavorite.DoesNotExist:
            return Response({"detail": "Favorite not found."}, status=status.HTTP_404_NOT_FOUND)

        favorite.delete()
        return Response({"detail": "Favorite removed."}, status=status.HTTP_200_OK)

class OrganizationToggleActiveView(generics.RetrieveUpdateAPIView):
    queryset = Organization.objects.all()
    serializer_class = OrganizationToggleActiveSerializer
    permission_classes = [IsAdminUser]

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
    """
    Create a new support request
    - User must be authenticated
    - User must have 'user' role
    - New requests start with status PENDING
    """
    serializer = HelpSupportCreateSerializer(data=request.data)
    
    if serializer.is_valid():
        # Save request with current user and set status to PENDING
        support_request = serializer.save(user=request.user, status=HelpSupport.Status.PENDING)
        
        # Return created request data
        response_serializer = HelpSupportSerializer(support_request)
        
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
    """
    Get support requests for the authenticated user
    """
    # Filter requests by type (optional)
    request_type = request.query_params.get('type')
    
    queryset = HelpSupport.objects.filter(user=request.user)
    
    if request_type:
        queryset = queryset.filter(type=request_type)
    
    # Order by creation date (newest first)
    queryset = queryset.order_by('-created_at')
    
    serializer = HelpSupportSerializer(queryset, many=True)
    
    return Response({
        'success': True,
        'data': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsUserRole])
def get_support_request_detail(request, pk):
    """
    Get details of a specific support request
    - Must belong to the authenticated user
    """
    support_request = get_object_or_404(
        HelpSupport, 
        pk=pk, 
        user=request.user
    )
    
    serializer = HelpSupportSerializer(support_request)
    
    return Response({
        'success': True,
        'data': serializer.data
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAdminRole])
def admin_send_request(request, pk):

    support_request = get_object_or_404(HelpSupport, pk=pk)

    if support_request.type == 'complaint':
        # تحقق من وجود target_org
        if not support_request.target_org:
            return Response(
                {'success': False, 'message': 'There must be a target organization for this complaint'},
                status=400
            )

    # تحديث الحالة إلى انتظار الرد
    support_request.status = HelpSupport.Status.WAITING_RESPONSE
    support_request.save()

    serializer = HelpSupportAdminSerializer(support_request)
    return Response({
        'success': True,
        'message': 'Complaint sent to organization and waiting for response',
        'data': serializer.data
    })

@api_view(['POST'])
@permission_classes([IsAdminRole])
def admin_reply_request(request, pk):
    """
    الرد على طلب عام أو حسابي من قبل الأدمن → CLOSED
    """
    support_request = get_object_or_404(
        HelpSupport,
        pk=pk,
        type__in=['general', 'account']  # فقط الطلبات العامة والحسابية
    )

    reply = request.data.get('reply')
    if not reply:
        return Response({'success': False, 'message': 'Reply is required'}, status=400)

    # حفظ الرد وتحويل الحالة إلى مغلق
    support_request.reply = reply
    support_request.status = HelpSupport.Status.CLOSED
    support_request.save()

    serializer = HelpSupportAdminSerializer(support_request)
    return Response({
        'success': True,
        'message': 'Request closed after admin reply',
        'data': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated, IsOrganizationRole])
def org_reply_request(request, pk):
    """
    المؤسسة ترد على شكوى → الطلب يصبح CLOSED
    - فقط المستخدم الذي لديه دور المؤسسة صاحب الطلب يمكنه الرد
    """
    support_request = get_object_or_404(
        HelpSupport, 
        pk=pk, 
        target_org__user=request.user,  # تأكيد أن المستخدم صاحب المؤسسة
        type='complaint'
    )

    reply = request.data.get('reply')
    if not reply:
        return Response({'success': False, 'message': 'Reply is required'}, status=400)

    # حفظ الرد وتحويل الحالة إلى مغلق
    support_request.reply = reply
    support_request.status = HelpSupport.Status.CLOSED
    support_request.save()

    serializer = HelpSupportAdminSerializer(support_request)
    return Response({
        'success': True,
        'message': 'Complaint closed after organization response',
        'data': serializer.data
    })