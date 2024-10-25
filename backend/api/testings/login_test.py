from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from ..submodels.models_user import Profile, PasswordResetToken, UserActivity
from django.test import override_settings
from io import BytesIO
from PIL import Image
import tempfile
import shutil

# Tạo một thư mục tạm thời cho MEDIA_ROOT trong quá trình testing
TEMP_MEDIA_ROOT = tempfile.mkdtemp()

class RegisterViewTest(APITestCase):
    def test_register_user(self):
        url = reverse('jwt')
        data = {
            'username': 'testuser',
            'password': 'testpassword123',
            'email': 'testuser@example.com'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue('tokens' in response.data)
        self.assertTrue(User.objects.filter(username='testuser').exists())

class LoginViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword123', email='testuser@example.com')
        self.profile = Profile.objects.create(user=self.user)

    def test_login_user(self):
        url = reverse('login')
        data = {
            'username': 'testuser',
            'password': 'testpassword123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

class ChangePasswordTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='oldpassword', email='testuser@example.com')
        self.client.force_authenticate(user=self.user)
    
    def test_change_password(self):
        url = reverse('change_password')
        data = {
            'old_password': 'oldpassword',
            'new_password': 'newpassword123'
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpassword123'))

@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class UploadAvatarUserTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword123', email='testuser@example.com')
        self.client.force_authenticate(user=self.user)
        self.profile = Profile.objects.create(user=self.user)

    def tearDown(self):
        # Xóa thư mục tạm thời sau khi test xong
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)
    
    def generate_image_file(self):
        file = BytesIO()
        image = Image.new('RGB', (100, 100))
        image.save(file, 'jpeg')
        file.name = 'test_image.jpg'
        file.seek(0)
        return file

    def test_upload_avatar(self):
        url = reverse('user_profile_avatar_upload')
        image = self.generate_image_file()
        data = {'avatar': image}
        response = self.client.post(url, data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.avatar.name.endswith('test_image.jpg'))

class ProfileViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword123', email='testuser@example.com')
        self.client.force_authenticate(user=self.user)
        self.profile = Profile.objects.create(user=self.user)

    def test_get_profile(self):
        url = reverse('profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['full_name'], self.profile.full_name)

    def test_update_profile(self):
        url = reverse('profile')
        data = {
            'full_name': 'New Full Name',
            'phone_number': '123456789',
            'gender': True,
            'english_level': 'B1',
            'daily_study_time': '1 hour'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.full_name, 'New Full Name')
        self.assertEqual(self.profile.phone_number, '123456789')

class PasswordResetRequestTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword123', email='testuser@example.com')

    def test_password_reset_request(self):
        url = reverse('password_reset_request')
        data = {'email': 'testuser@example.com'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(PasswordResetToken.objects.filter(uid=self.user.pk).exists())

class GoogleViewTest(APITestCase):
    def test_invalid_google_token(self):
        url = reverse('google')
        data = {'token_google': 'invalid_token'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

