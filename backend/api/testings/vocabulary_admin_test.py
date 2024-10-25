from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from ..submodels.models_vocabulary import *
from django.test import override_settings
from io import BytesIO
from PIL import Image
import tempfile
import shutil

# Tạo một thư mục tạm thời cho MEDIA_ROOT trong quá trình testing
TEMP_MEDIA_ROOT = tempfile.mkdtemp()

@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class AdminOnlyViewsTest(APITestCase):
    def setUp(self):
        # Setup admin user and authenticate
        self.admin_user = User.objects.create_user(username='admin', password='admin_pass')
        self.admin_user.is_superuser = True
        self.admin_user.save()
        self.admin_client = APIClient()
        # self.admin_client.login(username='admin', password='admin_pass')
        refresh_admin = RefreshToken.for_user(self.admin_user)
        self.admin_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh_admin.access_token}')
        
        # Create a non-admin user for access restriction tests
        self.non_admin_user = User.objects.create_user(username='user', password='user_pass')
        self.user_client = APIClient()
        refresh_user = RefreshToken.for_user(self.non_admin_user)
        self.user_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh_user.access_token}')
    
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
        
    def test_admin_access_to_view_vocabulary_list(self):
        """Test Admin can access the vocabulary list view."""
        url = reverse('admin_vocabulary_get_all')
        response = self.admin_client.get(url)
        
        # Verify Admin access
        self.assertEqual(response.status_code, status.HTTP_200_OK, "Admin should have access to vocabulary list")
        self.assertIn("results", response.data, "Vocabulary list should return a results field")

    def test_non_admin_access_restricted_to_view_vocabulary_list(self):
        """Test non-admin access is restricted for vocabulary list view."""
        # Log out Admin and log in as a non-admin user
        # self.user_client.logout()
        # self.user_client.login(username='user', password='user_pass')
        
        url = reverse('admin_vocabulary_get_all')
        response = self.user_client.get(url)
        
        # Verify access is forbidden for non-admins
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, "Non-admin should not have access to vocabulary list")

    def test_admin_can_create_vocabulary(self):
        """Test Admin can create a new vocabulary item."""
        url = reverse('admin_vocabulary_add')
        topic = Topic.objects.create(name="Topic 1")
        data = {
            "topic_id": topic.id,
            "word": "test",
            "definition": "This is a test definition",
            # Add other required fields based on your model
        }
        response = self.admin_client.post(url, data, format='json')
        
        # Verify creation success
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, "Admin should be able to create vocabulary")
        self.assertEqual(response.data['word'], data['word'], "The word should match the input data")

    def test_admin_can_update_vocabulary(self):
        """Test Admin can update a vocabulary item."""
        # First, create a vocabulary item to update
        create_url = reverse('admin_vocabulary_add')
        vocab_data = {"word": "initial", "definition": "Initial definition"}
        create_response = self.admin_client.post(create_url, vocab_data, format='json')
        
        # Now, update the created item
        vocab_id = create_response.data['error']
        update_url = reverse('admin_vocabulary_update_by_id')
        updated_data = {"word": "updated", "definition": "Updated definition"}
        
        response = self.admin_client.put(update_url, updated_data, format='json')
        
        # Verify update success
        self.assertEqual(response.status_code, status.HTTP_200_OK, "Admin should be able to update vocabulary")
        self.assertEqual(response.data['word'], updated_data['word'], "Updated word should match the input data")

    def test_non_admin_cannot_create_vocabulary(self):
        """Test non-admin cannot create a new vocabulary item."""
        # Log out Admin and log in as a non-admin user
        # self.client.logout()
        # self.client.login(username='user', password='user_pass')
        
        url = reverse('admin_vocabulary_add')
        data = {"word": "unauthorized", "definition": "Should not be created"}
        
        response = self.user_client.post(url, data, format='json')
        
        # Verify access is forbidden for non-admins
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, "Non-admin should not be able to create vocabulary")
