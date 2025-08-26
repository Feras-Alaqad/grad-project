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
    Announcement,
    UserFavorite,
    AnnouncementEditRequest,
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
    AnnouncementEditRequestCreateSerializer,
    AnnouncementEditRequestListSerializer,
    AnnouncementEditRequestDetailSerializer,
    AnnouncementEditRequestApprovalSerializer,
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
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # إنشاء توكن وريفريش
            refresh = RefreshToken.for_user(user)
            return Response({
                "success": True,
                "message": "User created successfully",
                "data": {
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
                }
            }, status=status.HTTP_201_CREATED)
        return Response({
            "success": False,
            "message": "Validation failed",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class OrganizationSignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if User.objects.filter(email=email).exists():
            return Response({
                "success": False,
                "message": "This email is already in use."
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = OrganizationSignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()  # إنشاء المستخدم والمؤسسة

            # لا يتم إصدار التوكن بعد، لأن الحساب غير مفعل
            return Response({
                "success": True,
                "message": "Your registration request has been received. Please wait for admin approval."
            }, status=status.HTTP_201_CREATED)

        return Response({
            "success": False,
            "message": "Validation failed",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

class OrganizationAcceptView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, org_id):
        try:
            org = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            return Response({
                "success": False,
                "message": "Organization not found."
            }, status=status.HTTP_404_NOT_FOUND)

        if org.is_active:
            return Response({
                "success": False,
                "message": "Organization is already active."
            }, status=status.HTTP_400_BAD_REQUEST)

        # تفعيل المؤسسة
        org.is_active = True
        org.is_rejected = False       # إعادة ضبط الرفض
        org.rejection_reason = ''
        org.save()

        # إنشاء التوكن للمستخدم المرتبط
        user = org.user
        refresh = RefreshToken.for_user(user)

        return Response({
            "success": True,
            "message": "Organization activated successfully.",
            "data": {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "phone": user.phone,
                    "role": user.role
                },
                "tokens": {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token)
                }
            }
        }, status=status.HTTP_200_OK)

class OrganizationRejectionView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, org_id):
        reason = request.data.get("reason", "")
        if not reason:
            return Response({
                "success": False,
                "message": "Rejection reason is required."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            org = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            return Response({
                "success": False,
                "message": "Organization not found."
            }, status=status.HTTP_404_NOT_FOUND)

        org.is_rejected = True
        org.rejection_reason = reason
        org.is_active = False
        org.save()

        return Response({
            "success": True,
            "message": "Organization has been rejected.",
            "data": {
                "reason": reason
            }
        }, status=status.HTTP_200_OK)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            return Response({
                'success': False,
                'message': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Authentication failed',
                'errors': serializer.errors if hasattr(serializer, 'errors') else str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user data
        user = serializer.user
        
        return Response({
            'success': True,
            'message': 'Login successful',
            'data': {
                'tokens': {
                    'refresh': serializer.validated_data['refresh'],
                    'access': serializer.validated_data['access']
                },
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'name': user.name,
                    'phone': user.phone,
                    'role': user.role
                }
            }
        }, status=status.HTTP_200_OK)
# views.py

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

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_jwt_token(request):
    """
    تحقق من صحة توكن JWT ويرجع رسالة مناسبة
    """
    token = request.data.get('token')

    if not token:
        return Response({
            "success": False,
            "message": "Token is required"
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # التحقق من التوكن
        UntypedToken(token)
        return Response({
            "success": True,
            "message": "Token is valid",
            "data": {
                "valid": True
            }
        }, status=status.HTTP_200_OK)
    except (InvalidToken, TokenError) as e:
        return Response({
            "success": False,
            "message": "Invalid or expired token",
            "data": {
                "valid": False
            }
        }, status=status.HTTP_401_UNAUTHORIZED)

    
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
            
            serializer = OrganizationProfileSerializer(organization)
            return Response({
                "success": True,
                "message": "Organization profile retrieved successfully",
                "data": serializer.data
            })
        else:
            serializer = UserSerializer(user)
            return Response({
                "success": True,
                "message": "User profile retrieved successfully",
                "data": serializer.data
            })
    def put(self, request):
        user = request.user

        forbidden_fields = ['website', 'location', 'description']
        if user.role == user.Role.USER:
            for field in forbidden_fields:
                if field in request.data:
                    return Response({
                        "success": False,
                        "message": "You are a USER, not an ORGANIZATION."
                    }, status=403)

        if user.role == user.Role.ORGANIZATION:
            try:
                organization = Organization.objects.get(user=user)
            except Organization.DoesNotExist:
                return Response({
                    "success": False,
                    "message": "Organization profile not found"
                }, status=404)

            serializer = OrganizationProfileSerializer(
                organization, data=request.data, partial=True
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
                "message": "Validation failed",
                "errors": serializer.errors
            }, status=400)
        
        else:
            serializer = UserSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    "success": True,
                    "message": "User profile updated successfully",
                    "data": serializer.data
                })
            return Response({
                "success": False,
                "message": "Validation failed",
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
    filterset_fields = ['category', 'organization', 'status']
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
        """Override list to return standard format"""
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
        
        # Serialize data with request context
        serializer = AnnouncementListSerializer(queryset, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'count': announcements.count(),
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

        serializer = UserFavoriteSerializer(favorite)
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


# Application views removed - announcements handle their own status workflow
# Users view approved announcements and apply through external URLs

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

