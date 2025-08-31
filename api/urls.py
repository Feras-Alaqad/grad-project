from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
from .views import (
    UserSignupView,
    OrganizationSignupView,
    OrganizationAcceptView,
    ForgotPasswordAPIView,
    ResetPasswordAPIView,
    ChangePasswordAPIView,
    ProfileView,
    CustomTokenObtainPairView,
    OrganizationRejectionView,
    AddFavoriteView,
    RemoveFavoriteView,
    AnnouncementViewSet,
    AnnouncementCategoryViewSet,
    CreateAnnouncementsView,
    UpdateAnnouncementView,
    OrganizationSearchView,
    OrganizationToggleActiveView,
    LogoutView,
    create_support_request,
    get_user_support_requests,  
    get_support_request_detail,
    admin_send_request,
    admin_reply_request,
    org_reply_request,
    OrganizationDocumentCreateView,
    OrganizationDocumentApproveRejectView
)

# Create router for ViewSets
router = DefaultRouter()
router.register(r'announcements', AnnouncementViewSet, basename='announcement')
router.register(r'announcement-categories', AnnouncementCategoryViewSet, basename='announcement-category')

urlpatterns = [
    # Authentication endpoints
    path('api/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path("api/auth/profile/", ProfileView.as_view(), name="user-profile"),
    path("api/auth/update-profile/", ProfileView.as_view(), name="update-profile"),
    path("api/auth/signup/user/", UserSignupView.as_view(), name="user-signup"),
    path("api/auth/signup/organization/", OrganizationSignupView.as_view(), name="organization-signup"),
    path('api/logout/', LogoutView.as_view(), name='logout'),
    path("api/organization/<int:org_id>/accept/", OrganizationAcceptView.as_view(), name="organization-activate"),
    path('api/organization/<int:org_id>/reject/', OrganizationRejectionView.as_view(), name='organization-reject'),
    path('api/favorites/add/<int:application_id>/', AddFavoriteView.as_view(), name='add-favorite'),
    path('api/favorites/remove/<int:application_id>/', RemoveFavoriteView.as_view(), name='remove-favorite'),
    path('api/auth/forgot-password/', ForgotPasswordAPIView.as_view(), name='forgot_password'),
    path('api/auth/reset-password/', ResetPasswordAPIView.as_view(), name='reset_password'),
    path('api/auth/change-password/', ChangePasswordAPIView.as_view(), name='change_password'),
    
    # Announcement endpoints
    path('api/create-announcements/', CreateAnnouncementsView.as_view(), name='create-announcements'),
    path('api/update-announcement/<int:pk>/', UpdateAnnouncementView.as_view(), name='update-announcement'),
    path('api/organizations/search/', OrganizationSearchView.as_view(), name='organization-search'),
    
    # Admin approval workflow endpoints
    path('api/announcements/pending/', AnnouncementViewSet.as_view({'get': 'pending_announcements'}), name='pending-announcements'),
    path('api/announcements/<int:pk>/approve/', AnnouncementViewSet.as_view({'patch': 'approve'}), name='approve-announcement'),
    path('api/announcements/my-announcements/', AnnouncementViewSet.as_view({'get': 'my_announcements'}), name='my-announcements'),
    path('api/organization/<int:pk>/block/', OrganizationToggleActiveView.as_view(), name='toggle-organization-active'),

    # Support request endpoints 
    path('api/support/create/', create_support_request, name='create_support_request'),
    path('api/support/my-requests/', get_user_support_requests, name='user_support_requests'),
    path('api/support/my-request/<int:pk>/', get_support_request_detail, name='support_request_detail'),
    path('api/admin/send-to-org/<int:pk>/', admin_send_request, name='admin-send-to-org'),
    path('api/admin/reply/<int:pk>/', admin_reply_request, name='admin-reply-request'),
    path('api/org/reply/<int:pk>/', org_reply_request, name='org-reply-request'),
    
    # Organization Document Management
    path("api/organization/documents/create/", OrganizationDocumentCreateView.as_view(), name="organization-documents-create"),
    path('api/admin/organization-documents/<int:id>/verify/', OrganizationDocumentApproveRejectView.as_view(), name='organization-documents-review'),


    # API endpoints (ViewSets)
    path('api/', include(router.urls)),
]