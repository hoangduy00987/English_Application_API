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
    class Meta:
        model = Topic
        fields = ['id','order','name', 'image','num_words','is_locked']

    def get_is_locked(self, obj):
        user = self.context['request'].user
        user_topic_process = UserTopicProgress.objects.filter(user_id=user,topic_id=obj).first()
        return user_topic_process.is_locked if user_topic_process else True
    def get_num_words(self, obj):
        return obj.vocabularies.filter(is_deleted=False).count()
    
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


#==========ADMIN

class AdminTopicSerializers(serializers.ModelSerializer):
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
            name = self.validated_data['name']
            # order = self.validated_data['order']
            image = self.validated_data['image']
            is_public = self.validated_data['is_public']
            model = Topic.objects.get(pk=topic_id)
            if not model.is_deleted:
                model.name = name
                # model.order = order
                model.image = image
                model.is_public=is_public
                model.save()
                return model
            raise serializers.ValidationError("Topic has Been deleted")
        except Exception as error:
            print("TopicSerializers_update_error: ", error)
            return None
    
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
            word = self.validated_data['word']
            transcription = self.validated_data['transcription']
            meaning = self.validated_data['meaning']
            example = self.validated_data['example']
            word_image = self.validated_data['word_image']
            pronunciation_audio = self.validated_data['pronunciation_audio']
            pronunciation_video = self.validated_data['pronunciation_video']
            order = self.validated_data['order']
            model = Vocabulary.objects.get(pk=vocabulary_id)
            if not model.is_deleted:
                model.word = word
                model.transcription = transcription
                model.meaning=meaning
                model.example = example
                model.word_image = word_image
                model.pronunciation_audio=pronunciation_audio
                model.pronunciation_video = pronunciation_video
                model.order=order
                model.save()
                return model
            raise serializers.ValidationError("Vocabulary has Been deleted")
        except Exception as error:
            print("VocabularySerializers_update_error: ", error)
            return None
    
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