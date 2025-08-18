from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import (
    SignupAPIView,
    ForgotPasswordAPIView,
    ResetPasswordAPIView,
    ChangePasswordAPIView,
    verify_jwt_token
    )

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', verify_jwt_token, name='token_verify'),
    path('api/auth/signup/', SignupAPIView.as_view(), name='signup'),
    path('api/auth/forgot-password/', ForgotPasswordAPIView.as_view(), name='forgot_password'),
    path('api/auth/reset-password/', ResetPasswordAPIView.as_view(), name='reset_password'),
    path('api/auth/change-password/', ChangePasswordAPIView.as_view(), name='change_password'),
]