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

from .models import (
    User, Organization,
    Announcement,
    UserFavorite,
    HelpSupport,
    OrganizationDocument,
    AnnouncementEditRequest,
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
    AnnouncementEditRequestListSerializer,
    AnnouncementEditRequestDetailSerializer,
    AnnouncementEditRequestApprovalSerializer,
    OrganizationToggleActiveSerializer,
    LogoutSerializer,
    HelpSupportAdminSerializer,
    HelpSupportSerializer,
    HelpSupportCreateSerializer,
    OrganizationDocumentSerializer,
    OrganizationSerializer,
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
                            "profile_image": request.build_absolute_uri(user.profile_image.url) if user.profile_image else None
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
            for field in ['name', 'email', 'phone']:
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

            # تحديث بيانات User الشخصية
            for field in ['name', 'email', 'phone']:
                if field in request.data:
                    setattr(user, field, request.data[field])
            user.save()

            # تحديث بيانات المؤسسة (description, website, location)
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
        serializer = UserFavoriteSerializer(favorites, many=True)
        
        return Response({
            "success": True,
            "data": serializer.data
        }, status=status.HTTP_200_OK)


# Application views removed - announcements handle their own status workflow
# Users view approved announcements and apply through external URLs

'''------------------------------------------------------------------------------------------------------------------------'''



class OrganizationToggleActiveView(generics.RetrieveUpdateAPIView):
    queryset = Organization.objects.all()
    serializer_class = OrganizationToggleActiveSerializer
    permission_classes = [IsAdminUser]

from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import User

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
        support_request = serializer.save(
            user=request.user,
            status=HelpSupport.Status.PENDING
        )
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
    # Get the support request
    support_request = get_object_or_404(HelpSupport, pk=pk)

    # Check type
    if support_request.type != HelpSupport.SupportType.ORGANIZATION:
        return Response({
            "success": False,
            "message": "This request is not of type 'Organization Complaint'."
        }, status=status.HTTP_400_BAD_REQUEST)

    # Check target organization
    if not support_request.target_org:
        return Response({
            "success": False,
            "message": "An organization request must have a target organization (target_org)."
        }, status=status.HTTP_400_BAD_REQUEST)

    # Update status
    support_request.status = HelpSupport.Status.WAITING_RESPONSE
    support_request.save()

    # Serialize response
    serializer = HelpSupportAdminSerializer(support_request)
    return Response({
        "success": True,
        "message": "Request sent to the organization and is now waiting for a response.",
        "data": serializer.data
    }, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsOrganizationRole])  # صلاحية المؤسسة فقط
def organization_admin_requests(request):
    # جلب المؤسسة المرتبطة بالمستخدم الحالي
    try:
        organization = Organization.objects.get(user=request.user)
    except Organization.DoesNotExist:
        return Response({
            "success": False,
            "message": "This user is not linked to any organization."
        }, status=403)

    # جلب الطلبات المرسلة من الأدمن للمؤسسة الحالية
    requests_qs = HelpSupport.objects.filter(
        target_org=organization,
        status=HelpSupport.Status.WAITING_RESPONSE
    ).order_by('-created_at')  # الأحدث أولاً

    serializer = HelpSupportAdminSerializer(requests_qs, many=True)
    return Response({
        "success": True,
        "count": requests_qs.count(),
        "message": "All requests sent by admin to your organization.",
        "data": serializer.data
    }, status=200)

@api_view(['POST'])
@permission_classes([IsAdminRole])
def admin_reply_request(request, pk):
    support_request = get_object_or_404(
        HelpSupport,
        pk=pk,
        type__in=[HelpSupport.SupportType.OTHER, HelpSupport.SupportType.SYSTEM]
    )

    reply = request.data.get('reply')
    if not reply:
        return Response({'success': False, 'message': 'Reply is required'}, status=400)

    # حفظ الرد وتحويل الحالة إلى CLOSED بعد الرد
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
    support_request = get_object_or_404(
        HelpSupport, 
        pk=pk, 
        target_org__user=request.user,
        type=HelpSupport.SupportType.ORGANIZATION
    )

    reply = request.data.get('reply')
    if not reply:
        return Response({'success': False, 'message': 'Reply is required'}, status=400)

    # حفظ الرد وتحويل الحالة إلى CLOSED بعد الرد من المؤسسة
    support_request.reply = reply
    support_request.status = HelpSupport.Status.CLOSED
    support_request.save()

    serializer = HelpSupportAdminSerializer(support_request)
    return Response({
        'success': True,
        'message': 'Request closed after organization response',
        'data': serializer.data
    })

@api_view(['POST'])
@permission_classes([IsAdminUser])
def approve_support_request(request, pk):
    """
    Admin approves a support request.
    - Only admin can perform this action
    - Changes the status to WAITING_RESPONSE
    """
    support_request = get_object_or_404(HelpSupport, pk=pk)

    # تحقق من أن الطلب لم يتم الرد عليه مسبقاً
    if support_request.status != HelpSupport.Status.PENDING:
        return Response({
            'success': False,
            'message': f"Cannot approve request with status '{support_request.status}'"
        }, status=status.HTTP_400_BAD_REQUEST)

    # تغيير الحالة إلى WAITING_RESPONSE
    support_request.status = HelpSupport.Status.WAITING_RESPONSE
    support_request.save()

    # إعادة البيانات بعد التحديث
    serializer = HelpSupportAdminSerializer(support_request)
    return Response({
        'success': True,
        'message': 'Support request approved and waiting for response',
        'data': serializer.data
    }, status=status.HTTP_200_OK)

class OrganizationDocumentCreateView(generics.CreateAPIView):
    """
    API لرفع وثائق المؤسسة
    المؤسسة تؤخذ تلقائياً من المستخدم المسجل دخول
    """
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
    permission_classes = [permissions.IsAuthenticated]  # يمكن تخصيصها لاحقاً
    queryset = Organization.objects.all()
    lookup_field = 'id'
