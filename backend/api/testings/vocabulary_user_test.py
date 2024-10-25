from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from ..submodels.models_vocabulary import Topic, Vocabulary, UserVocabularyProcess
from django.test import override_settings
from io import BytesIO
from PIL import Image
import tempfile
import shutil

# Tạo một thư mục tạm thời cho MEDIA_ROOT trong quá trình testing
TEMP_MEDIA_ROOT = tempfile.mkdtemp()

class UserTopicViewSetTest(APITestCase):
    def setUp(self):
        # Tạo user để test
        self.user = User.objects.create_user(username='testuser', password='testpass')

        # Tạo vài Topic để test
        self.topic1 = Topic.objects.create(name='Topic 1', order=1, is_public=True)
        self.topic2 = Topic.objects.create(name='Topic 2', order=2, is_public=True)

        # Đăng nhập
        self.client = APIClient()
        self.client.login(username='testuser', password='testpass')
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_get_all_topics(self):
        # Gọi API để lấy tất cả các topics
        url = reverse('topic_user_get_all')  # sử dụng url name từ views
        response = self.client.get(url)

        # Kiểm tra status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Kiểm tra số lượng topics trả về
        self.assertEqual(len(response.data['results']), 2)

class UserVocabularyViewSetTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')

        # Tạo Topic và Vocabulary
        self.topic = Topic.objects.create(name='Topic 1', is_public=True, order=1)
        self.vocabulary = Vocabulary.objects.create(
            topic_id=self.topic,
            word="apple",
            meaning="a fruit",
            transcription="/'æpl/",
            is_deleted=False,
        )

        self.client = APIClient()
        self.client.login(username='testuser', password='testpass')
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_get_vocabulary_to_learn(self):
        url = reverse('user_learn_vocabulary_get')  # sử dụng url name từ views
        response = self.client.get(url, {'topic_id': self.topic.id})

        # Kiểm tra status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Kiểm tra dữ liệu trả về
        self.assertEqual(response.data['word'], "apple")
        self.assertEqual(response.data['meaning'], "a fruit")

class UserVocabularyProcessViewSetTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')

        # Tạo Topic và Vocabulary
        self.topic = Topic.objects.create(name='Topic 1', is_public=True, order=1)
        self.vocabulary = Vocabulary.objects.create(
            topic_id=self.topic,
            word="apple",
            meaning="a fruit",
            transcription="/'æpl/",
            is_deleted=False,
        )

        self.client = APIClient()
        self.client.login(username='testuser', password='testpass')
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

    def test_post_learn_vocabulary(self):
        url = reverse('user_learn_vocabulary_post')  # sử dụng url name từ views
        data = {'vocabulary_id': self.vocabulary.id}
        response = self.client.post(url, data)

        # Kiểm tra status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Kiểm tra dữ liệu lưu vào database
        user_vocab_process = UserVocabularyProcess.objects.get(user_id=self.user, vocabulary_id=self.vocabulary)
        self.assertTrue(user_vocab_process.is_learned)

    def test_review_learned_vocabulary(self):
        # Tạo record để test review
        UserVocabularyProcess.objects.create(
            user_id=self.user, vocabulary_id=self.vocabulary, is_learned=True, review_count=1
        )

        url = reverse('user_learn_vocabulary_post')  # sử dụng url name từ views
        data = {'vocabulary_id': self.vocabulary.id}
        response = self.client.post(url, data)

        # Kiểm tra status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Kiểm tra số lần review đã được tăng lên
        user_vocab_process = UserVocabularyProcess.objects.get(user_id=self.user, vocabulary_id=self.vocabulary)
        self.assertEqual(user_vocab_process.review_count, 2)

    def test_set_next_review(self):
        url = reverse('set_next_review')
        data = {
            'vocabulary_id': self.vocabulary.id,
            'next_review_at': '2024-10-26T10:00:00'
        }
        UserVocabularyProcess.objects.create(
            user_id=self.user, vocabulary_id=self.vocabulary, is_learned=True
        )
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'Next review time updated successfully.')

    def test_set_next_review_fail(self):
        url = reverse('set_next_review')
        data = {
            'vocabulary_id': self.vocabulary.id,
            'next_review_at': '2024-10-26T10:00:00'
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], 'Vocabulary not learned yet or does not exist.')
