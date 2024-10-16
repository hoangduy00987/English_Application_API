
from django.urls import path
from .views import *


urlpatterns = [
    path('google/', GoogleView.as_view(), name='google'),
    path('register/', RegisterView.as_view(), name='jwt'),
    path('login/', LoginView.as_view(), name ='login'),
    path('change_password/', ChangePassword.as_view(), name='change_password'),
    path('user_profile_avatar_upload/', UploadAvatarUserView.as_view(),name="user_profile_avatar_upload"),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('password_reset_request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password_reset_confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('hello/', HelloWorld.as_view(), name='hello'),
]
