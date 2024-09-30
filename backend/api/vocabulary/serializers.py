from rest_framework import  serializers
from django.contrib.auth.models import User
from ..submodels.models_vocabulary import *
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from backend import settings
from django.core.validators import EmailValidator
from django.core.mail import send_mail, EmailMessage
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken


class TopicSerializers(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    num_words = serializers.SerializerMethodField()
    class Meta:
        model = Topic
        fields = ['id','order','name', 'image','num_words','is_locked']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None
    def get_num_words(self, obj):
        return obj.vocabularies.filter(is_deleted=False).count()


class VocabularySerializers(serializers.ModelSerializer):
    is_learned = serializers.SerializerMethodField()
    class Meta:
        model = Vocabulary
        fields = ['id', 'word','meaning','is_learned']

    def get_is_learned(self, obj):
        user = self.context['request'].user
        return UserVocabularyProcess.objects.filter(user_id=user,vocabulary_id=obj).exists()


class ListVocabularyOfTopicSerializers(serializers.ModelSerializer):
    vocabularies = VocabularySerializers(many=True, read_only=True)

    class Meta:
        model = Topic
        fields = ['id', 'name', 'vocabularies']

class LearnVocabularySerializers(serializers.ModelSerializer):
    pronunciation = serializers.SerializerMethodField()
    class Meta:
        model = Vocabulary
        fields = ['id','word','transcription','meaning','example','pronunciation']

    def get_pronunciation(self, obj):
        request = self.context.get('request')
        if obj.pronunciation:
            return request.build_absolute_uri(obj.pronunciation.url)
        return None

    
        
class UserVocabularyProcessSerializers(serializers.ModelSerializer):
    class Meta:
        model = UserVocabularyProcess
        fields = ['id','vocabulary_id']

    def save(self,request):
        try:
            vocabulary_id = self.validated_data['vocabulary_id']
            return UserVocabularyProcess.objects.create(user_id=request.user,vocabulary_id=vocabulary_id, is_learned=True)
        except Exception as error:
            print("UserVocabularyProcessSerializers_save_error: ", error)
            return None