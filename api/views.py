from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.conf import settings
from django.utils.html import strip_tags
from django.core.mail import send_mail
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

from .models import User
from .serializers import (
    UserSignupSerializer,
    UserSerializer,
    ForgotPasswordSerializer, 
    ResetPasswordSerializer,
    ChangePasswordSerializer
)


class SignupAPIView(generics.CreateAPIView):
    """
    API for registering new users
    """
    queryset = User.objects.all()
    serializer_class = UserSignupSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        
        # Create JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        user_data = UserSerializer(user).data
        
        return Response({
            'message': 'Account created successfully',
            'user': user_data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(access_token),
            }
        }, status=status.HTTP_201_CREATED)


# views.py
class ForgotPasswordAPIView(generics.GenericAPIView):
    """
    API for requesting password reset
    """
    serializer_class = ForgotPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.context['user']  # نستخدم context بدل validated_data
        token = default_token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

        # Generate reset URL
        reset_url = f"https://awn-three.vercel.app/reset-password/register/{uidb64}/{token}/"

        # Email content as plain text
        message = f"""
Hello {user.name or user.email},

You requested to reset your password.

Click the link below to reset your password:
{reset_url}

Or copy this link into your browser.

Note: This link is valid for a limited time only.
"""

        send_mail(
            subject='Password Reset',
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response({
            'message': 'Password reset link sent successfully',
            'email': user.email
        }, status=status.HTTP_200_OK)



class ResetPasswordAPIView(generics.GenericAPIView):
    """
    API for resetting password
    """
    serializer_class = ResetPasswordSerializer
    permission_classes = [AllowAny]

    def post(self, request, uidb64, token):
        serializer = self.get_serializer(
            data=request.data,
            context={'uidb64': uidb64, 'token': token}
        )
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']
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