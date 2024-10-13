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
from django.utils import timezone
from datetime import timedelta

#============USER
class UserTopicSerializers(serializers.ModelSerializer):
    is_locked = serializers.SerializerMethodField()
    num_words = serializers.SerializerMethodField()
    num_words_learned = serializers.SerializerMethodField()
    class Meta:
        model = Topic
        fields = ['id','order','name', 'image','num_words','num_words_learned','is_locked']

    def get_is_locked(self, obj):
        user = self.context['request'].user
        user_topic_process = UserTopicProgress.objects.filter(user_id=user,topic_id=obj).first()
        return user_topic_process.is_locked if user_topic_process else True
    
    def get_num_words(self, obj):
        return obj.vocabularies.filter(is_deleted=False).count()
    
    def get_num_words_learned(self, obj):
        user = self.context['request'].user
        topic_id = obj.id
        learned_count = UserVocabularyProcess.objects.filter(
            user_id=user,
            vocabulary_id__topic_id=topic_id,
            is_learned=True
        ).count()

        return learned_count



        
    def save(self, request):
        name = self.validated_data['name']
        order = self.validated_data['order']
        image = self.validated_data['image']
        return Topic.objects.create(name=name,order=order, image=image,created_at=datetime.now())
        
    

class VocabularySerializers(serializers.ModelSerializer):
    is_learned = serializers.SerializerMethodField()
    class Meta:
        model = Vocabulary
        fields = ['id', 'word','meaning','is_learned']

    def get_is_learned(self, obj):
        user = self.context['request'].user
        return UserVocabularyProcess.objects.filter(user_id=user,vocabulary_id=obj).exists()


class UserListVocabularyOfTopicSerializers(serializers.ModelSerializer):
    vocabularies = VocabularySerializers(many=True, read_only=True)

    class Meta:
        model = Topic
        fields = ['id', 'name', 'vocabularies']


        
class LearnVocabularySerializers(serializers.ModelSerializer):
    mini_exercises = serializers.SerializerMethodField()

    class Meta:
        model = Vocabulary
        fields = ['id','word','transcription','meaning','example','word_image','pronunciation_audio','pronunciation_video','mini_exercises']

    def get_mini_exercises(self, obj):
        mini_exercises = MiniExercise.objects.filter(vocabulary_id=obj).order_by('?')[:2]
        return MiniExerciseSerializers(mini_exercises, many=True).data

    
        
class UserVocabularyProcessSerializers(serializers.ModelSerializer):
    class Meta:
        model = UserVocabularyProcess
        fields = ['id','vocabulary_id']

    def save(self,request):
        try:
            vocabulary_id = self.validated_data['vocabulary_id']
            learned_at = timezone.localtime(timezone.now()) # Now
            next_review_at = learned_at + timedelta(days=1) # Review after 24h

            return UserVocabularyProcess.objects.create(
                user_id=request.user,
                vocabulary_id=vocabulary_id, 
                is_learned=True, 
                learned_at=learned_at,
                next_review_at=next_review_at
            )
        except Exception as error:
            print("UserVocabularyProcessSerializers_save_error: ", error)
            return None
        
class MiniExerciseSerializers(serializers.ModelSerializer):
    fillin_answers = serializers.SerializerMethodField()
    multiple_choice_answers = serializers.SerializerMethodField()

    class Meta:
        model = MiniExercise
        fields = ['id', 'exercise_type', 'content', 'fillin_answers', 'multiple_choice_answers']

    def get_fillin_answers(self, obj):
        # get answer from MiniExerciseFillinAnswer
        if obj.exercise_type == 'T1': # Fill in exercise
            fillin_answers = MiniExerciseFillinAnswer.objects.filter(exercise_id=obj)
            return MiniExerciseFillinAnswerSerializers(fillin_answers, many=True).data
        return None
    
    def get_multiple_choice_answers(self, obj):
        # get answer from MiniExerciseMultipleChoicesAnswer
        if obj.exercise_type == 'T2': # Multiple choice exercise
            multiple_choice_answers = MiniExerciseMultipleChoicesAnswer.objects.filter(exercise_id=obj)
            return MiniExerciseMultipleChoicesAnswerSerializers(multiple_choice_answers, many=True).data
        return None
        
class MiniExerciseFillinAnswerSerializers(serializers.ModelSerializer):
    class Meta:
        model = MiniExerciseFillinAnswer
        fields = ['id','correct_answer', 'available_answers']

class MiniExerciseMultipleChoicesAnswerSerializers(serializers.ModelSerializer):
    class Meta:
        model = MiniExerciseMultipleChoicesAnswer
        fields = ['id','answer', 'is_correct']

class ListVocabularyProcessOfUserSerializers(serializers.ModelSerializer):
    word = serializers.SerializerMethodField()
    class Meta:
        model = UserVocabularyProcess
        fields = ['id','learned_at','review_count','next_review_at','is_learned','word']

    def get_word(self, obj):
        vocabulary = Vocabulary.objects.get(word=obj)
        return vocabulary.word

class VocabularySerializer(serializers.ModelSerializer):
    class Meta:
        model = Vocabulary
        fields = ['id', 'word', 'meaning']

class VocabularyNeedReviewSerializer(serializers.ModelSerializer):
    vocabularies = VocabularySerializer(source='vocabulary_id') 

    class Meta:
        model = UserVocabularyProcess
        fields = ['id','vocabularies', 'last_learned_at', 'is_need_review']

#==========ADMIN==========

class AdminTopicSerializers(serializers.ModelSerializer):
    name = serializers.CharField(required=False)
    order = serializers.IntegerField(required=False)
    image = serializers.ImageField(required=False)

    num_words = serializers.SerializerMethodField()
    class Meta:
        model = Topic
        fields = ['id','order','name', 'image','num_words','is_public']
    def get_num_words(self, obj):
        return obj.vocabularies.filter(is_deleted=False).count()
    
    def save(self, request):
        try:
            name = self.validated_data['name']
            order = self.validated_data['order']
            image = self.validated_data['image']
            return Topic.objects.create(name=name,order=order, image=image,created_at=datetime.now())
        except Exception as error:
            print("TopicSerializers_save_error: ", error)
            return None
    def update(self, request):
        try:
            topic_id = request.query_params.get('topic_id')
            validated_data = self.validated_data
            model = Topic.objects.get(pk=topic_id)
            if model.is_deleted:
                raise serializers.ValidationError("Topic has been deleted.")
            model.name = validated_data.get('name', model.name)
            model.order = validated_data.get('order', model.order)
            model.image = validated_data.get('image', model.image)
            model.is_public = validated_data.get('is_public', model.is_public)
            model.save()
            return model
        except serializers.ValidationError as ve:
            print("TopicSerializers_update_validation_error: ", ve)
            raise ve
        except Exception as error:
            print("TopicSerializers_update_error: ", error)
            raise serializers.ValidationError("An error occurred while updating the Topic.")

    
    def delete(self, request):
        try:
            topic_id = request.query_params.get('topic_id')
            model = Topic.objects.get(pk=topic_id)
            if not model.is_deleted:
                model.is_deleted=True
                model.save()
                return model
            raise serializers.ValidationError("Topic has been deleted")
        except Exception as error:
            print("TopicSerializers_delete_error: ", error)
            return None
        
class AdminVocabularySerializers(serializers.ModelSerializer):
    class Meta:
        model = Vocabulary
        fields = ['id', 'word','meaning']   
class AdminVocabularyOfTopicSerializers(serializers.ModelSerializer):
    vocabularies = AdminVocabularySerializers(many=True)
    class Meta:
        model = Topic
        fields = ['id', 'name', 'vocabularies']

    
class AdminVocabularySerizlizers(serializers.ModelSerializer):
    topic_id = serializers.PrimaryKeyRelatedField(
        queryset=Topic.objects.all(), 
        required=False
    )
    word = serializers.CharField(required=False)
    transcription = serializers.CharField(required=False)
    meaning = serializers.CharField(required=False)
    example = serializers.CharField(required=False)
    word_image = serializers.ImageField(required=False)
    pronunciation_audio = serializers.FileField(required=False)
    pronunciation_video = serializers.FileField(required=False)
    order = serializers.IntegerField(required=False)
    class Meta:
        model = Vocabulary
        fields = ['id','topic_id','word','transcription','meaning','example','word_image','pronunciation_audio','pronunciation_video','order']

    def save(self, request):
        try:
            topic_id = self.validated_data['topic_id']
            word = self.validated_data['word']
            transcription = self.validated_data['transcription']
            meaning = self.validated_data['meaning']
            example = self.validated_data['example']
            word_image = self.validated_data['word_image']
            pronunciation_audio = self.validated_data['pronunciation_audio']
            pronunciation_video = self.validated_data['pronunciation_video']
            order = self.validated_data['order']
            return Vocabulary.objects.create(
                topic_id=topic_id,
                word=word,
                transcription=transcription, 
                meaning=meaning, 
                example=example, 
                word_image=word_image, 
                pronunciation_audio=pronunciation_audio, 
                pronunciation_video=pronunciation_video, 
                order=order, 
                created_at=datetime.now())
        except Exception as error:
            print("VocabularySerializers_save_error: ", error)
            return None
        
    def update(self, request):
        try:
            vocabulary_id = request.query_params.get('vocabulary_id')
            validated_data = self.validated_data
            model = Vocabulary.objects.get(pk=vocabulary_id)
            if model.is_deleted:
                raise serializers.ValidationError("Vocabulary has been deleted.")
            model.word = validated_data.get('word', model.word)
            model.transcription = validated_data.get('transcription', model.transcription)
            model.meaning = validated_data.get('meaning', model.meaning)
            model.example = validated_data.get('example', model.example)
            model.word_image = validated_data.get('word_image', model.word_image)
            model.pronunciation_audio = validated_data.get('pronunciation_audio', model.pronunciation_audio)
            model.pronunciation_video = validated_data.get('pronunciation_video', model.pronunciation_video)
            model.order = validated_data.get('order', model.order)
            model.save()

            return model
        except Vocabulary.DoesNotExist:
            raise serializers.ValidationError("Vocabulary not found.")
        except Exception as error:
            print("VocabularySerializers_save_error: ", error)
            raise serializers.ValidationError("An error occurred while updating the Vocabulary.")

    
    def delete(self, request):
        try:
            vocabulary_id = request.query_params.get('vocabulary_id')
            model = Vocabulary.objects.get(pk=vocabulary_id)
            if not model.is_deleted:
                model.is_deleted=True
                model.save()
                return model
            raise serializers.ValidationError("Vocabulary has been deleted")
        except Exception as error:
            print("VocabuarySerializers_delete_error: ", error)
            return None