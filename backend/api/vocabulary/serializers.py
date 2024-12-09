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
from ..submodels.models_user import *
#============USER
class UserTopicSerializers(serializers.ModelSerializer):
    is_locked = serializers.SerializerMethodField()
    num_words = serializers.SerializerMethodField()
    num_words_learned = serializers.SerializerMethodField()
    class Meta:
        model = Topic
        fields = ['id','name', 'image','num_words','num_words_learned','is_locked']

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
        
        image = self.validated_data['image']
        return Topic.objects.create(name=name, image=image,created_at=datetime.now())
        
class UserCourseSerializers(serializers.ModelSerializer):
    list_topic = serializers.SerializerMethodField()
    class Meta:
        model = Course
        fields = ['id','name','image','description','list_topic']    

    def get_list_topic(self, obj):
        topics = Topic.objects.filter(course_id=obj.id, is_deleted=False, is_public=True).order_by('id')

        if topics.exists():
            first_topic = topics.first()

            user_topic, created = UserTopicProgress.objects.get_or_create(
                user_id=self.context['request'].user,
                topic_id=first_topic
            )
            user_topic.is_locked = False
            user_topic.save()

        return UserTopicSerializers(topics, many=True, context=self.context).data


class TeacherCourseSerializers(serializers.ModelSerializer):
    list_topic = serializers.SerializerMethodField()
    class Meta:
        model = Course
        fields = ['id','name','image','description','list_topic']    

    def get_list_topic(self, obj):
        topics = Topic.objects.filter(course_id=obj.id, is_deleted=False).order_by('-updated_at')
        return AdminTopicSerializers(topics, many=True, context=self.context).data

class VocabularySerializers(serializers.ModelSerializer):
    is_learned = serializers.SerializerMethodField()
    class Meta:
        model = Vocabulary
        fields = ['id', 'word','meaning','is_learned']

    def get_is_learned(self, obj):
        user = self.context['request'].user
        return UserVocabularyProcess.objects.filter(user_id=user,vocabulary_id=obj).exists()


class UserListVocabularyOfTopicSerializers(serializers.ModelSerializer):
    vocabularies = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = ['id', 'name', 'vocabularies']

    def get_vocabularies(self, obj):
        # Lấy tất cả từ vựng liên quan đến topic này và có is_deleted=False
        active_vocabularies = Vocabulary.objects.filter(topic_id=obj, is_deleted=False).order_by('-updated_at')
        # Trả về dữ liệu đã được serialize
        return AdminVocabularySerializers(active_vocabularies, many=True).data
        
class LearnVocabularySerializers(serializers.ModelSerializer):
    mini_exercises = serializers.SerializerMethodField()

    class Meta:
        model = Vocabulary
        fields = ['id','word','transcription','meaning','example','word_image','pronunciation_audio','pronunciation_video','mini_exercises']

    def get_mini_exercises(self, obj):
        mini_exercises = MiniExercise.objects.filter(vocabulary_id=obj, is_deleted=False).order_by('id')
        return MiniExerciseSerializers(mini_exercises, many=True).data
    

class ReviewVocabularySerializers(serializers.ModelSerializer):
    class Meta:
        model = Vocabulary
        fields = ['id','word','transcription','meaning','example','word_image','pronunciation_audio','pronunciation_video']

    
        
class UserVocabularyProcessSerializers(serializers.ModelSerializer):
    class Meta:
        model = UserVocabularyProcess
        fields = ['id','vocabulary_id']

    def save(self,request):
        try:
            vocabulary_id = self.validated_data['vocabulary_id']
            last_learned_at = timezone.now()

            return UserVocabularyProcess.objects.create(
                user_id=request.user,
                vocabulary_id=vocabulary_id, 
                is_learned=True, 
                last_learned_at=last_learned_at,
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
        fields = ['id','correct_answer']

class MiniExerciseMultipleChoicesAnswerSerializers(serializers.ModelSerializer):
    class Meta:
        model = MiniExerciseMultipleChoicesAnswer
        fields = ['id','answer', 'is_correct']

class ListVocabularyProcessOfUserSerializers(serializers.ModelSerializer):
    word = serializers.SerializerMethodField()
    class Meta:
        model = UserVocabularyProcess
        fields = ['id','last_learned_at','review_count','next_review_at','is_learned','word']

    def get_word(self, obj):
        vocabulary = Vocabulary.objects.filter(
            word=obj.vocabulary_id.word
        ).first()
        return vocabulary.word

class ListLearnedVocabularyOfUserSerializers(serializers.ModelSerializer):
    word = serializers.SerializerMethodField()
    meaning = serializers.SerializerMethodField()
    transcription = serializers.SerializerMethodField()
    example = serializers.SerializerMethodField()

    class Meta:
        model = UserVocabularyProcess
        fields = ['id', 'word', 'meaning', 'transcription', 'example']
    
    def get_word(self, obj):
        vocabulary = Vocabulary.objects.filter(
            word=obj.vocabulary_id.word
        ).first()
        return vocabulary.word
    
    def get_meaning(self, obj):
        vocabulary = Vocabulary.objects.filter(
            word=obj.vocabulary_id.word
        ).first()
        return vocabulary.meaning
    
    def get_transcription(self, obj):
        vocabulary = Vocabulary.objects.filter(
            word=obj.vocabulary_id.word
        ).first()
        return vocabulary.transcription
    
    def get_example(self, obj):
        vocabulary = Vocabulary.objects.filter(
            word=obj.vocabulary_id.word
        ).first()
        return vocabulary.example

class VocabularySerializer(serializers.ModelSerializer):
    class Meta:
        model = Vocabulary
        fields = ['id', 'word', 'meaning']


#==========ADMIN==========
class TeacherManageCourseSerializers(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id','name','image','description','is_public']

    def save(self, request):
        try:
            name = self.validated_data['name']
            image = self.validated_data['image']
            description = self.validated_data['description']
            is_public = self.validated_data['is_public']
            return Course.objects.create(name=name,image=image, description=description,is_deleted=False,is_public=is_public)
        except Exception as error:
            print("CourseSerializers_save_error: ", error)
            return None
        
    def update(self, request):
        try:
            course_id = request.query_params.get('course_id')
            if not course_id:
                raise serializers.ValidationError("course_id is required.")
            
            validated_data = self.validated_data
            try:
                model = Course.objects.get(pk=course_id)
            except Course.DoesNotExist:
                raise serializers.ValidationError("Course not found.")
            if model.is_deleted:
                raise serializers.ValidationError("Course has been deleted.")
            model.name = validated_data.get('name', model.name)
            model.image = validated_data.get('image', model.image)
            model.description = validated_data.get('description', model.description) 
            model.is_public = validated_data.get('is_public', model.is_public)
            model.update_at = timezone.now()
            model.save()
            return model
        except serializers.ValidationError as ve:
            print("CourseSerializers_update_validation_error:", ve)
            raise ve
        except Exception as error:
            print("CourseSerializers_update_error:", error)
            raise serializers.ValidationError("An error occurred while updating the Course.")

    
    def delete(self, request):
        try:
            course_id = request.query_params.get('course_id')
            if not course_id:
                raise serializers.ValidationError("course_id is required.")
            model = Course.objects.get(pk=course_id)
            if not model.is_deleted:
                model.is_deleted=True
                model.save()
                return model
            raise serializers.ValidationError("Course has been deleted")
        except Exception as error:
            print("CourseSerializers_delete_error: ", error)
            return None
        
class AdminTopicSerializers(serializers.ModelSerializer):
    name = serializers.CharField(required=False)
    image = serializers.ImageField(required=False)
    course_id = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all(),required=False)
    num_words = serializers.SerializerMethodField()
    class Meta:
        model = Topic
        fields = ['id','course_id','name', 'image','num_words','is_public']
    def get_num_words(self, obj):
        return obj.vocabularies.filter(is_deleted=False).count()
    
    def save(self, request):
        try:
            course_id = self.validated_data['course_id']
            name = self.validated_data['name']
            image = self.validated_data['image']
            return Topic.objects.create(course_id=course_id,name=name, image=image,created_at=datetime.now())
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
    vocabularies = serializers.SerializerMethodField()
    class Meta:
        model = Topic
        fields = ['id', 'name', 'vocabularies']

    def get_vocabularies(self, obj):
        # Lấy tất cả từ vựng liên quan đến topic này và có is_deleted=False
        active_vocabularies = Vocabulary.objects.filter(topic_id=obj, is_deleted=False).order_by('-updated_at')
        # Trả về dữ liệu đã được serialize
        return AdminVocabularySerializers(active_vocabularies, many=True).data

class AdminVocabularySerializers(serializers.ModelSerializer):
    topic_id = serializers.PrimaryKeyRelatedField(queryset=Topic.objects.all(), required=True)
    word = serializers.CharField(required=False)
    transcription = serializers.CharField(required=False)
    meaning = serializers.CharField(required=False)
    example = serializers.CharField(required=False)
    word_image = serializers.ImageField(required=False)
    pronunciation_audio = serializers.FileField(required=False)
    pronunciation_video = serializers.FileField(required=False)
    class Meta:
        model = Vocabulary
        fields = ['id','topic_id','word','transcription','meaning','example','word_image','pronunciation_audio','pronunciation_video']
    
    def save(self, request):
        try:
            validated_data = self.validated_data
            print("Validated data: ", validated_data)
            topic_id = validated_data.get('topic_id')
            word = validated_data.get('word')
            transcription = validated_data.get('transcription')
            meaning = validated_data.get('meaning')
            example = validated_data.get('example')
            word_image = validated_data.get('word_image')
            pronunciation_audio = validated_data.get('pronunciation_audio')
            pronunciation_video = validated_data.get('pronunciation_video')
            vocabulary = Vocabulary.objects.create(
                topic_id=topic_id,
                word=word,
                transcription=transcription,
                meaning=meaning,
                example=example,
                word_image=word_image,
                pronunciation_audio=pronunciation_audio,
                pronunciation_video=pronunciation_video,
                created_at=timezone.now(),
                updated_at=timezone.now()
            )

            return vocabulary

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
        

# ==== Mini Exercise ====
class AdminMiniExerciseSerializers(serializers.ModelSerializer):
    content = serializers.SerializerMethodField()
    class Meta:
        model = MiniExercise
        fields = ['id', 'vocabulary_id', 'exercise_type', 'content']

    def get_content(self, obj):
        return f'{obj.content} - {obj.vocabulary_id.word}'


# Fill in exercise =====================
class AdminFillinAnswerExerciseSerializers(serializers.ModelSerializer):
    vocabulary = serializers.SerializerMethodField()
    answers = serializers.SerializerMethodField()
    class Meta:
        model = MiniExercise
        fields = ['id', 'vocabulary', 'exercise_type', 'content', 'answers']

    def get_vocabulary(self, obj):
        return obj.vocabulary_id.word
    
    def get_answers(self, obj):
        if obj.exercise_type == "T1":
            answers = MiniExerciseFillinAnswer.objects.filter(exercise_id=obj)
            return MiniExerciseFillinAnswerSerializers(answers, many=True).data
        return None
        

class AdminManageAnswerFillinExerciseSerializers(serializers.ModelSerializer):
    correct_answer = serializers.CharField(required=True)

    class Meta:
        model = MiniExerciseFillinAnswer
        fields = ['correct_answer']


class AdminManageFillinExerciseSerializers(serializers.ModelSerializer):
    vocabulary_id = serializers.IntegerField(required=True)
    content = serializers.CharField(required=True)
    answer = AdminManageAnswerFillinExerciseSerializers()

    class Meta:
        model = MiniExercise
        fields = ['id','vocabulary_id','content','answer']

    def save(self, request):
        try:
            vocabulary_id = self.validated_data['vocabulary_id']
            content = self.validated_data['content']
            answer = self.validated_data.pop('answer')
            vocabulary = Vocabulary.objects.get(id=vocabulary_id, is_deleted=False)
            exercise = MiniExercise.objects.create(
                vocabulary_id=vocabulary,
                exercise_type="T1",
                content=content
            )
            MiniExerciseFillinAnswer.objects.create(
                exercise_id=exercise,
                **answer
            )
            return exercise
        except Vocabulary.DoesNotExist:
            raise serializers.ValidationError({"error": "Vocabulary not found."})
        except Exception as error:
            print("AdminManageFillinExerciseSerializers_error:", error)
            return None
        
    def update(self, request):
        try:
            exercise_id = request.query_params.get('exercise_id')
            validated_data = self.validated_data
            answer = validated_data.pop('answer')
            model = MiniExercise.objects.get(pk=exercise_id)
            if model.is_deleted:
                raise serializers.ValidationError({"error": "This fill in exercise was deleted."})
            vocabulary_id = validated_data.get('vocabulary_id', model.vocabulary_id.id)
            vocabulary = Vocabulary.objects.get(id=vocabulary_id, is_deleted=False)
            model.vocabulary_id = vocabulary
            model.content = validated_data.get('content', model.content)
            model.save()
            answer_model = MiniExerciseFillinAnswer.objects.get(exercise_id=model)
            answer_model.correct_answer = answer.get('correct_answer', answer_model.correct_answer)
            answer_model.save()
            return model
        except MiniExercise.DoesNotExist:
            raise serializers.ValidationError({"error": "Fill in exercise not found."})
        except Vocabulary.DoesNotExist:
            raise serializers.ValidationError({"error": "Vocabulary not found"})
        except Exception as error:
            print("update_fill_in_exercise_error:", error)
            return None
        
    def delete(self, request):
        try:
            exercise_id = request.query_params.get('exercise_id')
            exercise = MiniExercise.objects.get(pk=exercise_id)
            if not exercise.is_deleted:
                exercise.is_deleted = True
                exercise.save()
                return exercise
            raise serializers.ValidationError({"error": "This fill in exercise is already deleted."})
        except MiniExercise.DoesNotExist:
            raise serializers.ValidationError({"error": "Fill in exercise not found."})
        except Exception as error:
            print("delete_fill_in_exercise_error:", error)
            return None


# Multiple choices exercise ==============
class AdminMultipleChoicesAnswerExerciseSerializers(serializers.ModelSerializer):
    vocabulary = serializers.SerializerMethodField()
    answers = serializers.SerializerMethodField()
    class Meta:
        model = MiniExercise
        fields = ['id', 'vocabulary', 'exercise_type', 'content', 'answers']

    def get_vocabulary(self, obj):
        return obj.vocabulary_id.word
    
    def get_answers(self, obj):
        if obj.exercise_type == "T2":
            answers = MiniExerciseMultipleChoicesAnswer.objects.filter(exercise_id=obj)
            return MiniExerciseMultipleChoicesAnswerSerializers(answers, many=True).data
        return None
        

class AdminManageAnswerMultipleChoicesExerciseSerializers(serializers.ModelSerializer):
    answer = serializers.CharField(required=True)
    is_correct = serializers.BooleanField(required=True)

    class Meta:
        model = MiniExerciseFillinAnswer
        fields = ['answer','is_correct']


class AdminManageMultipleChoicesExerciseSerializers(serializers.ModelSerializer):
    vocabulary_id = serializers.IntegerField(required=True)
    content = serializers.CharField(required=True)
    answers = AdminManageAnswerMultipleChoicesExerciseSerializers(many=True)

    class Meta:
        model = MiniExercise
        fields = ['id','vocabulary_id','content','answers']

    def save(self, request):
        try:
            vocabulary_id = self.validated_data['vocabulary_id']
            content = self.validated_data['content']
            answers_data = self.validated_data.pop('answers')
            vocabulary = Vocabulary.objects.get(id=vocabulary_id, is_deleted=False)
            exercise = MiniExercise.objects.create(
                vocabulary_id=vocabulary,
                exercise_type="T2",
                content=content
            )
            answers = [
                MiniExerciseMultipleChoicesAnswer(
                    exercise_id=exercise,
                    **answer_data
                )
                for answer_data in answers_data
            ]
            MiniExerciseMultipleChoicesAnswer.objects.bulk_create(answers)
            return exercise
        except Vocabulary.DoesNotExist:
            raise serializers.ValidationError({"error": "Vocabulary not found."})
        except Exception as error:
            print("add_multiple_choices_exercise_error:", error)
            return None
        
    def update(self, request):
        try:
            exercise_id = request.query_params.get('exercise_id')
            validated_data = self.validated_data
            answers_data = validated_data.pop('answers')
            model = MiniExercise.objects.get(pk=exercise_id)
            if model.is_deleted:
                raise serializers.ValidationError({"error": "This multiple choices exercise was deleted."})
            vocabulary_id = validated_data.get('vocabulary_id', model.vocabulary_id.id)
            vocabulary = Vocabulary.objects.get(id=vocabulary_id, is_deleted=False)
            model.vocabulary_id = vocabulary
            model.content = validated_data.get('content', model.content)
            model.save()
            answers_model = list(MiniExerciseMultipleChoicesAnswer.objects.filter(exercise_id=model)[:4])
            for i, answer_data in enumerate(answers_data):
                answers_model[i].answer = answer_data.get('answer', answers_model[i].answer)
                answers_model[i].is_correct = answer_data.get('is_correct', answers_model[i].is_correct)
            
            MiniExerciseMultipleChoicesAnswer.objects.bulk_update(answers_model, ['answer', 'is_correct'])
            return model
        except MiniExercise.DoesNotExist:
            raise serializers.ValidationError({"error": "Multiple choices exercise not found."})
        except Vocabulary.DoesNotExist:
            raise serializers.ValidationError({"error": "Vocabulary not found"})
        except Exception as error:
            print("update_multiple_choices_exercise_error:", error)
            return None
        
    def delete(self, request):
        try:
            exercise_id = request.query_params.get('exercise_id')
            exercise = MiniExercise.objects.get(pk=exercise_id)
            if not exercise.is_deleted:
                exercise.is_deleted = True
                exercise.save()
                return exercise
            raise serializers.ValidationError({"error": "This multiple choices exercise is already deleted."})
        except MiniExercise.DoesNotExist:
            raise serializers.ValidationError({"error": "Multiple choices exercise not found."})
        except Exception as error:
            print("delete_multiple_choices_exercise_error:", error)
            return None


class StudentEnrollCourseSerializers(serializers.ModelSerializer):
    emails = serializers.ListField(child=serializers.EmailField(), allow_empty=False)
    course_id = serializers.IntegerField()
    class Meta:
        model = UserCourseEnrollment
        fields = ['emails','course_id']

    
    def enroll(self, request):
        try:
            # Kiểm tra xem email có được cung cấp hay không
            emails = self.validated_data.get('emails', [])
            if not emails:
                return {"errors": ["No emails provided. Please include at least one email."]}

            course_id = self.validated_data.get('course_id')
            course = Course.objects.get(id=course_id)

            results = {
                "enrolled_students": [],
                "errors": []
            }

            for email in emails:
                try:
                    student = User.objects.get(email=email)
                    if UserCourseEnrollment.objects.filter(user_id=student, course_id=course).exists():
                        results["errors"].append(
                            f"User with email {email} is already enrolled in course {course_id}."
                        )
                    else:
                        # Tạo bản ghi mới nếu chưa tồn tại
                        UserCourseEnrollment.objects.create(
                            user_id=student, course_id=course, enrolled_at=timezone.now()
                        )
                        results["enrolled_students"].append(email)

                except User.DoesNotExist:
                    results["errors"].append(f"Student with email {email} does not exist.")

            return results

        except Course.DoesNotExist:
            return {"errors": [f"Course with ID {course_id} does not exist."]}
        except Exception as error:
            print("Error:", error)
            return {"errors": ["An unexpected error occurred."]}




    def delete(self, request):
        try:
            emails = request.data.get('emails')
            course_id = request.data.get('course_id')
            for email in emails:
                student = User.objects.get(email=email)
                model = UserCourseEnrollment.objects.filter(user_id=student,course_id=course_id)
                model.delete()
        except Exception as error:
            print("error: ", error)
            return None

class AudioFileSerializer(serializers.Serializer):
    audio_file = serializers.FileField()

    def validate_audio_file(self, value):
        allowed_extensions = ['.wav', '.mp3', '.m4a']
        if not any(value.name.endswith(ext) for ext in allowed_extensions):
            raise serializers.ValidationError("Only .wav, .mp3, and .m4a files are supported.")
        return value

class StudentSerializer(serializers.ModelSerializer):
    enrolled_at = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ["email",'full_name','enrolled_at']
    def get_enrolled_at(self, user):
        try:
            enrollment = UserCourseEnrollment.objects.filter(user_id=user).first()
            return enrollment.enrolled_at 

        except UserCourseEnrollment.DoesNotExist:
            return None
    def get_full_name(self, user):
        try:
            full_name = Profile.objects.get(user_id=user)
            return full_name.full_name 

        except Profile.DoesNotExist:
            return None 
        
    

class StudentCourseSerializers(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id','name','image','description','is_public']

class StudentProgressSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    class Meta:
        model = UserTopicProgress
        fields = []