from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.core.mail import send_mail
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import (
    User, Organization,
    Announcement, Application,
    UserFavorite
)
from .serializers import (
    UserSignupSerializer,
    UserSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
    OrganizationSignupSerializer,
    OrganizationProfileSerializer,
    CustomTokenObtainPairSerializer,
    UserFavoriteSerializer
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
# views.py
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
    
class AddFavoriteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, announcement_id):
        user = request.user
        try:
            announcement = Announcement.objects.get(id=announcement_id)
        except Announcement.DoesNotExist:
            return Response({"detail": "Announcement not found."}, status=status.HTTP_404_NOT_FOUND)

        # التحقق من وجود Application مع is_favorite = True
        try:
            app = Application.objects.get(user=user, announcement=announcement, is_favorite=True)
        except Application.DoesNotExist:
            return Response({"detail": "Cannot add to favorites. Application is not marked as favorite."},
                            status=status.HTTP_400_BAD_REQUEST)

        favorite, created = UserFavorite.objects.get_or_create(user=user, announcement=announcement)
        serializer = UserFavoriteSerializer(favorite)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class RemoveFavoriteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, announcement_id):
        user = request.user
        try:
            favorite = UserFavorite.objects.get(user=user, announcement_id=announcement_id)
        except UserFavorite.DoesNotExist:
            return Response({"detail": "Favorite not found."}, status=status.HTTP_404_NOT_FOUND)

        favorite.delete()
        return Response({"detail": "Announcement removed from favorites."}, status=status.HTTP_200_OK)