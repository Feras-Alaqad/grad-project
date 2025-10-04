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
    OrganizationToggleActiveView,
    AddFavoriteView,
    RemoveFavoriteView,
    ListFavoritesView,
    LogoutView,
    create_support_request,
    get_user_support_requests,  
    get_support_request_detail,
    admin_reply_request,
    OrganizationDocumentCreateView,
    OrganizationDocumentApproveRejectView,
    list_all_documents,
    OrganizationDocumentDetailAPIView,
    OrganizationListAPIView,
    ToggleBlockUserAPIView,
    UserListAPIView,
    UserDetailAPIView,
    UserSearchAPIView,
    OrganizationDetailAPIView,
    VerifiedOrganizationListAPIView,
    HelpSupportListView,
    admin_support_request_detail,
    help_support_range_search,
    SendNotificationAllUsersView,
    UserNotificationsView,
    SendNotificationToUserView,
    NotificationListView,
    SendNotificationToOrganizationsView,
    NotificationDeleteView,
    NotificationDeleteAllView,
    AdminNotificationDeleteView,
    OrganizationVerificationAPIView,
    DeleteUserView,
    DeleteOrganizationView,
    OrganizationListView,
    OrganizationActiveFilterAPIView,
    AdminStatisticsAPIView,
    AdminTimeSeriesStatisticsAPIView,
    password_reset_email_preview,

)

# router for ViewSets
router = DefaultRouter()
router.register(r'announcements', AnnouncementViewSet, basename='announcement')
router.register(r'announcement-categories', AnnouncementCategoryViewSet, basename='announcement-category')


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
    path('api/auth/email-preview/password-reset/', password_reset_email_preview, name='email-preview-password-reset'),
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


    

    path('api/users/', UserListAPIView.as_view(), name='user-list'),
    path('api/users/<int:id>/', UserDetailAPIView.as_view(), name='user-detail'),
    path('api/users/search/', UserSearchAPIView.as_view(), name='user-search'),
    path('api/organization/<int:pk>/block-unblock/', OrganizationToggleActiveView.as_view(), name='toggle-organization-active'),
    path('api/users/<int:user_id>/block-unblock/', ToggleBlockUserAPIView.as_view(), name='block-unblock-user'),


    # Support request endpoints
    path('api/support/create/', create_support_request, name='create_support_request'),
    path('api/support/my-requests/', get_user_support_requests, name='user_support_requests'),
    path('api/support/my-request/<int:pk>/', get_support_request_detail, name='support_request_detail'),
    path('api/support/admin/reply/<int:pk>/', admin_reply_request, name='admin-reply-support'),
    path("api/help-support-list/", HelpSupportListView.as_view(), name="help-support-list"),
    path("api/help-support-details/<int:pk>/", admin_support_request_detail, name="admin-support-request-detail"),
    path("api/help-support/range/search/", help_support_range_search, name="help_support_range_search"),


    # Organization Document Management
    path("api/organization/documents/create/", OrganizationDocumentCreateView.as_view(), name="organization-documents-create"),
    path('api/admin/organization-documents/<int:id>/verify/', OrganizationDocumentApproveRejectView.as_view(), name='organization-documents-review'),
    path('api/admin/organizationdocuments/', list_all_documents, name='organization-documents-list'),
    path('api/admin/organizationdocument/<int:pk>/', OrganizationDocumentDetailAPIView.as_view(), name='organization-document-detail'),
    path('api/admin/organizations/<int:pk>/verify/', OrganizationVerificationAPIView.as_view(), name='organization-verify'),

    # organization endpoints
    path('api/organizations/', OrganizationListAPIView.as_view(), name='organization-list'),
    path('api/organizations/<int:id>/', OrganizationDetailAPIView.as_view(), name='organization-detail'),
    path('api/organizations/verified/', VerifiedOrganizationListAPIView.as_view(), name='verified-organizations'),
    path('api/users/delete/<int:user_id>/', DeleteUserView.as_view(), name='delete-user'),
    path('api/organizations/delete/<int:org_id>/', DeleteOrganizationView.as_view(), name='delete-organization'),
    path('api/admin/organizations/', OrganizationListView.as_view(), name='organization-list'),
    path('api/organizations/active-filter/', OrganizationActiveFilterAPIView.as_view(), name='organization-list'),

    # notification endpoints can be added here
    path('api/notifications/send-to-users/', SendNotificationAllUsersView.as_view(), name='send-notifications-users'),
    path('api/notifications/send-to-organizations/', SendNotificationToOrganizationsView.as_view(), name='send-notification-organizations'),
    path('api/my/notifications/', UserNotificationsView.as_view(), name='my-notifications'),
    path('api/notifications/send-to-user/', SendNotificationToUserView.as_view(), name='send-notification-to-user'),
    path('api/notifications/', NotificationListView.as_view(), name='notification-list'),
    path('api/notification/<int:pk>/delete/', NotificationDeleteView.as_view(), name='notification-delete'),
    path('api/notifications/delete-all/', NotificationDeleteAllView.as_view(), name='notification-delete-all'),
    path('api/admin/notification/<int:pk>/delete/', AdminNotificationDeleteView.as_view(), name='admin-notification-delete'),
    path('api/admin/statistics/', AdminStatisticsAPIView.as_view(), name='admin-statistics'),
    path('api/admin/statistics/timeseries/', AdminTimeSeriesStatisticsAPIView.as_view(), name='admin-statistics-timeseries'),
    # api app endpoints (ViewSets)
    path('api/', include(router.urls)),
]
