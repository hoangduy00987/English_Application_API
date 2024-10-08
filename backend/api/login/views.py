from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.hashers import make_password
from rest_framework.views import APIView
from rest_framework.response import Response
import requests
from rest_framework.permissions import IsAuthenticated
from .serializers import *
from ..submodels.models_user import *
from rest_framework.views import APIView
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings

from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework.response import Response
from rest_framework import status

class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = TokenRefreshSerializer

    def post(self, request):
        # Lấy refresh token từ request body
        serializer = self.get_serializer(data=request.data)

        try:
            # Kiểm tra tính hợp lệ của refresh token
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            # Trả về lỗi nếu refresh token không hợp lệ hoặc hết hạn
            return Response(
                {"detail": "Refresh token không hợp lệ hoặc đã hết hạn."}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Lấy dữ liệu sau khi kiểm tra thành công (gồm access token mới)
        response_data = serializer.validated_data

        return Response(response_data, status=status.HTTP_200_OK)

class GoogleView(APIView):
    def post(self, request):
        # get token Google from request
        token_google = request.data.get("token_google")
        if not token_google:
            return Response({'message': 'invalid token.'}, status=status.HTTP_400_BAD_REQUEST)
        # send request to Google to validate token
        payload = {'access_token': token_google}
        response = requests.get('https://www.googleapis.com/oauth2/v3/userinfo', params=payload)
        
        if response.status_code != 200:
            return Response({'message': 'error  connecting to google'}, status=status.HTTP_400_BAD_REQUEST)
        
        data = response.json()
        
        if 'error' in data:
            return Response({'message': 'Token Google is invalid or expired.'}, status=status.HTTP_400_BAD_REQUEST)

        #  get infomation from  Google response
        email = data.get("email")
        if not email:
           return Response({'message': 'Unable to receive email from Google token.'}, status=status.HTTP_400_BAD_REQUEST)

        # create user if doesn't exist
        user, created = User.objects.get_or_create(email=email, defaults={
            'username': email,
            'password': make_password(BaseUserManager().make_random_password()),
        })
        is_first_login = False
        if created:
            profile = Profile.objects.create(
            user=user,created_at=datetime.now()
            )
            is_first_login = profile.is_first_login
            
        # Create And Response token to user
        token = RefreshToken.for_user(user)
        response_data = {
            'access': str(token.access_token),
            'refresh': str(token),
            'is_first_login': is_first_login
        }
        response = Response(response_data,status=status.HTTP_200_OK)

        if is_first_login:
            # Update the flag to False after sending the response
            profile.is_first_login = False
            profile.save()

        return response

class RegisterView(APIView):
    serializer_class = RegisterSerializers

    def post(self, request, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                user = serializer.save(request=request) 

                refresh = RefreshToken.for_user(user)
                tokens = {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    "is_first_login": True
                }
                return Response({
                    "tokens": tokens
                }, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("error", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView): 

    def post(self, request):
        try:
            serializer = LoginSerializers(data=request.data)
            if serializer.is_valid():
                user = serializer.validated_data['user']
                refresh = RefreshToken.for_user(user)

                return Response(
                    {
                        'refresh': str(refresh),
                        'access': str(refresh.access_token),
                        'is_superuser': user.is_superuser  # Thêm thông tin is_superuser vào phản hồi
                    },
                    status=status.HTTP_200_OK
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("error", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    
class ChangePassword(APIView):
    serializer_class = ChangePasswordSerializers
    permission_classes = [IsAuthenticated]

    def put(self, request):
        try:
            serializer = ChangePasswordSerializers(data=request.data, context={'request': request})
            if serializer.is_valid():
                serializer.update()
                return Response({'message': 'Password updated successfully'}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("error", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        


class UploadAvatarUserView(APIView):
    serializer_class = UploadAvatarUserSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            data={}
            if serializer.is_valid():
                serializer.update_avatar(request=request)
                data['message'] = 'Avatar uploaded successfuly!'
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("upload_avatar: ", error)
            return Response({'error': 'Bad request'}, status=status.HTTP_400_BAD_REQUEST)
        

class ProfileView(APIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def post(self,request):
        try:
            serializer = self.serializer_class(data=request.data)
            data = {}
            if serializer.is_valid():
                serializer.update(request=request)
                data['message'] = 'Update Student profile successfully!'
                return Response(data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("error: ", error)
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
    
    def get(self,request):
        try:
            queryset = Profile.objects.get(user=request.user)
            serializer = self.serializer_class(queryset, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as error:
            print("error: ", error)
            return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetRequestView(APIView):
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
                token = default_token_generator.make_token(user)
                PasswordResetToken.objects.create(uid=user.pk, token=token)
                uid = user.pk
                reset_link = f"http://localhost:3000/reset-password-server/{uid}/{token}/"
                send_mail(
                    'Reset your password',
                    f'Click the link below to reset your password:\n{reset_link}',
                    settings.EMAIL_HOST_USER,
                    [email],
                    fail_silently=False,
                )
                return Response({'message': 'Password reset link sent.'}, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                return Response({'message': 'Email not found.'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class PasswordResetConfirmView(APIView):
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            uid = serializer.validated_data['uid']
            token = serializer.validated_data['token']
            new_password = serializer.validated_data['new_password']

            try:
                user = User.objects.get(pk=uid)
                reset_token = PasswordResetToken.objects.get(uid=uid, token=token)

                if reset_token.is_used:
                    return Response({'message': 'This link has already been used.'}, status=status.HTTP_400_BAD_REQUEST)

                if not default_token_generator.check_token(user, token):
                    return Response({'message': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)

                # Mark token as used
                reset_token.is_used = True
                reset_token.save()

                user.set_password(new_password)
                user.save()

                return Response({'message': 'Password has been reset successfully.'}, status=status.HTTP_200_OK)
            
            except User.DoesNotExist:
                return Response({'message': 'Invalid user.'}, status=status.HTTP_400_BAD_REQUEST)
            except PasswordResetToken.DoesNotExist:
                return Response({'message': 'Invalid reset token.'}, status=status.HTTP_400_BAD_REQUEST)
            #hello

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)