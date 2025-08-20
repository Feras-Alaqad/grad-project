from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    UserSignupView,
    OrganizationSignupView,
    OrganizationActivationView,
    ForgotPasswordAPIView,
    ResetPasswordAPIView,
    ChangePasswordAPIView,
    verify_jwt_token,
    ProfileView,
    CustomTokenObtainPairView
    )

urlpatterns = [
    path('api/auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/verify/', verify_jwt_token, name='token_verify'),
    path("api/auth/profile/", ProfileView.as_view(), name="profile"),
    path("api/auth/update-profile/", ProfileView.as_view(), name="update-profile"),
    path("api/auth/signup/user/", UserSignupView.as_view(), name="user-signup"),
    path("api/auth/signup/organization/", OrganizationSignupView.as_view(), name="organization-signup"),
    path("api/organizations/<int:org_id>/activate/", OrganizationActivationView.as_view(), name="organization-activate"),
    path('api/auth/forgot-password/', ForgotPasswordAPIView.as_view(), name='forgot_password'),
    path('api/auth/reset-password/', ResetPasswordAPIView.as_view(), name='reset_password'),
    path('api/auth/change-password/', ChangePasswordAPIView.as_view(), name='change_password'),
]