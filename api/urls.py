from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    UserSignupView,
    OrganizationSignupView,
    OrganizationAcceptView,
    ForgotPasswordAPIView,
    ResetPasswordAPIView,
    ChangePasswordAPIView,
    verify_jwt_token,
    ProfileView,
    CustomTokenObtainPairView,
    OrganizationRejectionView,
    AddFavoriteView,
    RemoveFavoriteView,
    AnnouncementViewSet,
    AnnouncementCategoryViewSet,
    ApplicationViewSet,
    CreateAnnouncementsView,
    UpdateAnnouncementView,
    OrganizationSearchView
)

# Create router for ViewSets
router = DefaultRouter()
router.register(r'announcements', AnnouncementViewSet, basename='announcement')
router.register(r'announcement-categories', AnnouncementCategoryViewSet, basename='announcement-category')
router.register(r'applications', ApplicationViewSet, basename='application')

urlpatterns = [
    # Authentication endpoints
    path('api/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/verify/', verify_jwt_token, name='token_verify'),
    path("api/auth/profile/", ProfileView.as_view(), name="user-profile"),
    path("api/auth/signup/user/", UserSignupView.as_view(), name="user-signup"),
    path("api/auth/signup/organization/", OrganizationSignupView.as_view(), name="organization-signup"),
    path("api/organization/<int:org_id>/accept/", OrganizationAcceptView.as_view(), name="organization-activate"),
    path('api/organization/<int:org_id>/reject/', OrganizationRejectionView.as_view(), name='organization-reject'),
    path('api/announcements/<int:announcement_id>/favorite/add/', AddFavoriteView.as_view(), name='add-favorite'),
    path('api/announcements/<int:announcement_id>/favorite/remove/', RemoveFavoriteView.as_view(), name='remove-favorite'),
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
    

    # API endpoints (ViewSets)
    path('api/', include(router.urls)),
]
