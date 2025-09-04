from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    UserSignupView,
    OrganizationSignupView,
    ForgotPasswordAPIView,
    ResetPasswordAPIView,
    ChangePasswordAPIView,
    ProfileView,
    AnnouncementViewSet,
    AnnouncementCategoryViewSet,
    CreateAnnouncementsView,
    UpdateAnnouncementView,
    OrganizationSearchView,
    OrganizationCreateAnnouncementView,
    DeleteAnnouncementView,
    AnnouncementEditRequestViewSet,
    OrganizationToggleActiveView,
    AddFavoriteView,
    RemoveFavoriteView,
    ListFavoritesView,
    LogoutView,
    create_support_request,
    get_user_support_requests,  
    get_support_request_detail,
    send_request_to_organization,
    organization_admin_requests,
    admin_reply_request,
    org_reply_request,
    OrganizationDocumentCreateView,
    OrganizationDocumentApproveRejectView,
)

# Create router for ViewSets
router = DefaultRouter()
router.register(r'announcements', AnnouncementViewSet, basename='announcement')
router.register(r'announcement-categories', AnnouncementCategoryViewSet, basename='announcement-category')
router.register(r'announcement-edit-requests', AnnouncementEditRequestViewSet, basename='announcement-edit-request')

urlpatterns = [
    # Authentication endpoints
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path("api/auth/profile/", ProfileView.as_view(), name="user-profile"),
    path("api/auth/update-profile/", ProfileView.as_view(), name="update-profile"),
    path("api/auth/signup/user/", UserSignupView.as_view(), name="user-signup"),
    path("api/auth/signup/organization/", OrganizationSignupView.as_view(), name="organization-signup"),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/favorites/add/<int:announcement_id>/', AddFavoriteView.as_view(), name='add-favorite'),
    path('api/favorites/remove/<int:announcement_id>/', RemoveFavoriteView.as_view(), name='remove-favorite'),
    path('api/favorites/', ListFavoritesView.as_view(), name='list-favorites'),
    path('api/auth/forgot-password/', ForgotPasswordAPIView.as_view(), name='forgot_password'),
    path('api/auth/reset-password/', ResetPasswordAPIView.as_view(), name='reset_password'),
    path('api/auth/change-password/', ChangePasswordAPIView.as_view(), name='change_password'),
    
    # Announcement endpoints
    path('api/create-announcements/', CreateAnnouncementsView.as_view(), name='create-announcements'),
    path('api/organizations/create-announcement/', OrganizationCreateAnnouncementView.as_view(), name='organization-create-announcement'),
    path('api/update-announcement/<int:pk>/', UpdateAnnouncementView.as_view(), name='update-announcement'),
    path('api/delete-announcement/<int:pk>/', DeleteAnnouncementView.as_view(), name='delete-announcement'),
    path('api/organizations/search/', OrganizationSearchView.as_view(), name='organization-search'),
    
    # Admin approval workflow endpoints
    path('api/announcements/pending/', AnnouncementViewSet.as_view({'get': 'pending_announcements'}), name='pending-announcements'),
    path('api/announcements/<int:pk>/approve/', AnnouncementViewSet.as_view({'patch': 'approve'}), name='approve-announcement'),
    path('api/announcements/my-announcements/', AnnouncementViewSet.as_view({'get': 'my_announcements'}), name='my-announcements'),

    # Edit request endpoints
    path('api/edit-requests/pending/', AnnouncementEditRequestViewSet.as_view({'get': 'pending_edit_requests'}), name='pending-edit-requests'),
    path('api/edit-requests/<int:pk>/approve-reject/', AnnouncementEditRequestViewSet.as_view({'patch': 'approve_reject'}), name='approve-reject-edit-request'),
    
    # Application URLs removed - announcements handle their own status workflow
    # Users view approved announcements and apply through external URLs
    
    path('api/organization/<int:pk>/block/', OrganizationToggleActiveView.as_view(), name='toggle-organization-active'),


    # Support request endpoints 
    path('api/support/create/', create_support_request, name='create_support_request'),
    path('api/support/my-requests/', get_user_support_requests, name='user_support_requests'),
    path('api/support/my-request/<int:pk>/', get_support_request_detail, name='support_request_detail'),
    path('api/admin/send-to-org/<int:pk>/', send_request_to_organization, name='admin-send-to-org'),
    path("api/received_admin_requests/", organization_admin_requests, name="received_admin_requests"),
    path('api/admin/reply/<int:pk>/', admin_reply_request, name='admin-reply-request'),
    path('api/org/reply/<int:pk>/', org_reply_request, name='org-reply-request'),

    
    # Organization Document Management
    path("api/organization/documents/create/", OrganizationDocumentCreateView.as_view(), name="organization-documents-create"),
    path('api/admin/organization-documents/<int:id>/verify/', OrganizationDocumentApproveRejectView.as_view(), name='organization-documents-review'),


    # API endpoints (ViewSets)
    path('api/', include(router.urls)),
]
