from rest_framework import  serializers
from django.contrib.auth.models import User
from ..submodels.models_user import *
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework.response import Response
from rest_framework import status

class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = TokenRefreshSerializer

    def post(self, request, *args, **kwargs):
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
    
class RegisterSerializers(serializers.ModelSerializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True,write_only=True)
    email = serializers.EmailField(required=True)
    class Meta:
        model = User
        fields = ['username','password','email']
        extra_kwargs = {
            'password':{'write_only': True},
        }

    def validate_email(self,value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email already exists.')
        return value
    def validate_username(self,value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username already exists.')
        return value
    
    def save(self, request):
        username = self.validated_data['username']
        password = self.validated_data['password']
        email = self.validated_data['email']
        user = User.objects.create_user(username=username,password=password,email=email)
        Profile.objects.create(user=user,created_at=datetime.now())
        return user
    


class LoginSerializers(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                if not user.is_active:
                    raise AuthenticationFailed('User account is disabled.')
                return {'user': user}
            else:
                raise AuthenticationFailed('Invalid credentials.')
        else:
            raise serializers.ValidationError('Must include "username_or_email" and "password".')

    
class ChangePasswordSerializers(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        user = self.context['request'].user
        if not user.check_password(data['old_password']):
            raise serializers.ValidationError({'message': 'Old password is incorrect.'})
        return data
    
    def update(self):
        user = self.context['request'].user
        new_password = self.validated_data['new_password']
        user.set_password(new_password)
        user.save()
        return user

class UploadAvatarUserSerializer(serializers.ModelSerializer):
    avatar = serializers.FileField(required=True)

    class Meta:
        model = Profile
        fields = ["avatar"]

    def update_avatar(self,request):
        try:
            avatar = self.validated_data["avatar"]
            model = Profile.objects.get(user=request.user)
            model.avatar = avatar
            model.save()
            return model
        except Exception as error:
            print("UploadAvatarUserSerializer_update_avatar_error: ", error)
            return None

class ProfileSerializer(serializers.ModelSerializer):
    # full_name = serializers.CharField(required=True)
    # english_level = serializers.CharField(required=True)
    # daily_study_time = serializers.CharField(required=True)
    # phone_number = serializers.CharField(required=True)   
    # gender = serializers.BooleanField(required=True)
    class Meta:
        model = Profile
        fields = [
            "avatar",
            "full_name",
            "gender",
            "english_level",
            "daily_study_time",
            "phone_number"
        ]

    def update(self, request):
        try:
            validated_data = self.validated_data
            profile = Profile.objects.get(user=request.user)
            fields_to_update = [
                                "full_name",
                                "gender",
                                "english_level",
                                "daily_study_time",
                                "phone_number"
                                ]

            for field in fields_to_update:
                setattr(profile, field, validated_data[field])
                
            profile.updated_at = datetime.now()
            profile.save()
            return profile
        except Exception as error:
            print("Profile_update_error:", error)
            return None


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField()