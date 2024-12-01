from rest_framework.response import Response
from rest_framework import status,viewsets
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated,IsAdminUser
from .serializers import *
from ..submodels.models_user import *
from rest_framework.views import APIView
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from .serializers import *
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
import random 
from django.utils import timezone
from datetime import datetime,timedelta
from django.db.models import Q
import torch
from transformers import Wav2Vec2ForCTC, Wav2Vec2Tokenizer
import librosa
from .serializers import AudioFileSerializer



class HistoryLogPagination(PageNumberPagination):
    page_size = 2
    page_size_query_param = 'page_size'
    max_page_size = 10

    def get_paginated_response(self, data):
        next_page = previous_page = None
        if self.page.has_next():
            next_page = self.page.next_page_number()
        if self.page.has_previous():
            previous_page = self.page.previous_page_number()
        return Response({
            'totalRows': self.page.paginator.count,
            'page_size': self.page_size,
            'current_page': self.page.number,
            'next_page': next_page,
            'previous_page': previous_page,
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link(),
            },
            'results': data,
        })

def update_leader_board(user, points, course_id):
    try:
        course = Course.objects.get(id=course_id) 
        
        leaderboard, created = LeaderBoard.objects.get_or_create(user=user, course=course)
        

        leaderboard.weekly_points += points
        leaderboard.monthly_points += points
        leaderboard.total_points += points
        now = timezone.now()
        leaderboard.year_week = now.isocalendar()[1]
        leaderboard.year_month = now.month
        leaderboard.update_at = timezone.now()

        
        leaderboard.save()

    except Course.DoesNotExist:
        print("Course not found.")
    except Exception as error:
        print("Error updating leaderboard: ", error)

# get all topic
class StudentTopicViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = HistoryLogPagination
    serializer_class = UserCourseSerializers
    @action(methods=['GET'], detail=False, url_path="topic_user_get_all", url_name="topic_user_get_all")
    def topic_user_get_all(self, request):
        try:
            course_id = request.query_params.get("course_id")
            if not course_id:
                return Response({"message": "Course ID is required."}, status=status.HTTP_400_BAD_REQUEST)

            course = Course.objects.filter(id=course_id, is_deleted=False)
            if not course:
                return Response({"message": "Course Not Found"}, status=status.HTTP_404_NOT_FOUND)  
            page = self.paginate_queryset(course)
            if page is not None:
                serializer = self.get_serializer(page, many=True, context={'request': request})
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(course, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as error:
            print("error:", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    

#Get vocabuylray to learn
class UserVocabularyViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = LearnVocabularySerializers
    @action(methods='GET', detail=False, url_path="user_learn_vocabulary_get", url_name="user_learn_vocabulary_get")
    def user_learn_vocabulary_get(self, request):
        try:
            topic_id = request.query_params.get('topic_id')
            topic = Topic.objects.get(id=topic_id, is_deleted=False, is_public=True)
            vocabulary_list = topic.vocabularies.filter(is_deleted=False)
            learned_vocab_ids = UserVocabularyProcess.objects.filter(
                user_id=request.user, is_learned=True
            ).values_list('vocabulary_id', flat=True)
            remaining_vocab = vocabulary_list.exclude(id__in=learned_vocab_ids).first()
            
            if remaining_vocab:
                serializer = self.serializer_class(remaining_vocab, context={'request': request})
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                next_topic = Topic.objects.filter(id__gt=topic.id,
                                                       is_deleted=False, is_public=True).first()
                print(next_topic)
                if next_topic:
                    next_user_topic,created = UserTopicProgress.objects.get_or_create(
                        user_id=request.user,
                        topic_id=next_topic
                    )
                    next_user_topic.is_locked = False
                    next_user_topic.save()
                learned_vocab = vocabulary_list.filter(id__in=learned_vocab_ids)
                next_vocab = random.choice(learned_vocab)
                serializer = self.serializer_class(next_vocab, context={'request': request})
                return Response({
                    "message": "All vocabulary has been learned, now reviewing.",
                    "vocabulary": serializer.data
                }, status=status.HTTP_200_OK)
        except Topic.DoesNotExist:
            return Response({"message": "Topic Not Found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as error:
            print('error:', error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)

# save word learned
class UserVocabularyProcessViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserVocabularyProcessSerializers
    @action(methods='POST', detail=False, url_path="user_learn_vocabulary_post", url_name="user_learn_vocabulary_post")
    def user_learn_vocabulary_post(self, request):
        try:
            vocabulary_id = request.data.get('vocabulary_id')

            if not vocabulary_id:
                return Response({"message": "vocabulary_id is required."}, status=status.HTTP_400_BAD_REQUEST)
            
            # check user did learned this vocabulary
            user_vocab_process = UserVocabularyProcess.objects.filter(
                user_id=request.user,
                vocabulary_id=vocabulary_id
            ).first()

            if user_vocab_process:
                user_vocab_process.review_count = (user_vocab_process.review_count or 0) + 1
                user_vocab_process.is_need_review = False
                user_vocab_process.is_learned = True
                user_vocab_process.last_learned_at = timezone.now()
                user_vocab_process.save()
                
                update_leader_board(request.user, 5 , user_vocab_process.vocabulary_id.topic_id.course_id.id)
                return Response({'message':'You have finished reviewing this word.'}, status=status.HTTP_200_OK)
            else:
                serializer = self.serializer_class(data=request.data)
                if serializer.is_valid():
                    serializer.save(request=request)
                    return Response({'message':'You have finished studying this word.'}, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as error:
            print("error", error) 
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(methods=['POST'], detail=False, url_path="set_next_review", url_name="set_next_review")
    def set_next_review(self, request):
        try:
            vocabulary_id = request.data.get('vocabulary_id')
            next_review_at_str = request.data.get('next_review_at')

            if not vocabulary_id or not next_review_at_str:
                return Response({"message": "Missing vocabulary_id or next_review_at"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Parse the next_review_at string to a datetime object
            try:
                next_review_at = datetime.fromisoformat(next_review_at_str)
                next_review_at = timezone.make_aware(next_review_at, timezone.get_current_timezone())
            except ValueError:
                return Response({"message": "Invalid date format for next_review_at"}, status=status.HTTP_400_BAD_REQUEST)
            
            # check if vocabulary is learned yet
            user_vocab_process = UserVocabularyProcess.objects.filter(
                user_id=request.user,
                vocabulary_id=vocabulary_id,
                is_learned=True
            ).first()

            if not user_vocab_process:
                return Response({"message": "Vocabulary not learned yet or does not exist."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate next_review_at
            if next_review_at < timezone.localtime(timezone.now()):
                return Response({"message": "Review time must be after the current time."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Update next_review_at
            user_vocab_process.next_review_at = next_review_at
            user_vocab_process.save()

            return Response({"message": "Next review time updated successfully."}, status=status.HTTP_200_OK)
        
        except Exception as error:
            print("set_next_review_error:", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(methods=['GET'], detail=False, url_path="user_vocab_process", url_name="user_vocab_process")
    def user_vocab_process(self, request):
        try:
            # get all process of current user
            user_vocab_records = UserVocabularyProcess.objects.filter(user_id=request.user)

            # Serialize data
            serializer = ListVocabularyProcessOfUserSerializers(user_vocab_records, many=True)

            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as error:
            print("error", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(methods=['POST'], detail=False, url_path="user_skip_vocabulary", url_name="user_skip_vocabulary")
    def user_skip_vocabulary(self, request):
        try:
            vocabulary_id = request.data.get('vocabulary_id')
            
            if not vocabulary_id:
                return Response({'message': 'Vocabulary ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

            # Kiểm tra xem Vocabulary có tồn tại hay không
            try:
                vocabulary = Vocabulary.objects.get(id=vocabulary_id)
            except Vocabulary.DoesNotExist:
                return Response({'message': 'Vocabulary not found.'}, status=status.HTTP_404_NOT_FOUND)

            # Kiểm tra nếu đã tồn tại một bản ghi cho người dùng và từ vựng này
            user_vocabulary_process, created = UserVocabularyProcess.objects.get_or_create(
                user_id=request.user,
                vocabulary_id=vocabulary,
                defaults={'is_skipped': True}
            )

            # Nếu bản ghi đã tồn tại và không phải bản ghi mới, chỉ cần cập nhật is_skipped
            if not created:
                user_vocabulary_process.is_skipped = True
                user_vocabulary_process.save()

            return Response({'message': 'Word has been successfully skipped'}, status=status.HTTP_200_OK)
            
        except Exception as error:
            return Response({'message': 'An error occurred.', 'details': str(error)}, status=status.HTTP_400_BAD_REQUEST)



#get all vocabulary of topic
class UserListVocabularyViewSet(APIView):
    serializer_class = UserListVocabularyOfTopicSerializers
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            topic_id = request.query_params.get('topic_id')
            topic = Topic.objects.get(id=topic_id, is_public=True, is_deleted=False,)
            serializer = self.serializer_class(topic, context={'request':request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Topic.DoesNotExist:
            return Response({"message": "Topic Not Found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as error:
            print('error: ', error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        



#============Admin==========
class TeacherManageTopicViewset(viewsets.ModelViewSet):
    serializer_class = AdminTopicSerializers
    pagination_class = HistoryLogPagination
    permission_classes = [IsAdminUser]

   
    @action(methods='GET', detail=True, url_path="admin_topic_get_by_id", url_name="admin_topic_get_by_id")
    def admin_topic_get_by_id(self, request):
        try:
            topic_id = request.query_params.get("topic_id")
            queryset = Topic.objects.get(id=topic_id,is_deleted=False)
            serializer = self.serializer_class(queryset, context={'request':request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Topic.DoesNotExist:
            return Response({"message":"Topic Not Found"},status=status.HTTP_404_NOT_FOUND)
        except Exception as error:
            print("error", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods="POST", detail=False, url_path="admin_topic_add", url_name="admin_topic_add")
    def admin_topic_add(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                topic = serializer.save(request=request)
                return Response({"message":"topic added successfuly"}, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("error", error) 
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(methods="PATCH", detail=False, url_path="admin_topic_update_by_id", url_name="admin_topic_update_by_id")
    def admin_topic_update_by_id(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                update_model = serializer.update(request=request)
                if update_model is None:
                    return Response({"message": "Topic not found."}, status=status.HTTP_404_NOT_FOUND)
                return Response({"message":"topic updated successfuly"}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("error", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(methods="DELETE", detail=False, url_path="admin_topic_delete_by_id", url_name="admin_topic_delete_by_id")
    def admin_topic_delete_by_id(self, request):
        try:
            queryset = self.serializer_class()
            delete_model = queryset.delete(request=request)
            if delete_model is None:
                 return Response({"message": "Topic not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response({"message": "Topic  deleted successfully"}, status=status.HTTP_200_OK)  
        except Exception as error:
            print("error", error) 
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)

class TeacherListVocabularyViewSet(viewsets.ModelViewSet):
    serializer_class = AdminVocabularyOfTopicSerializers
    permission_classes = [IsAdminUser]

    @action(methods="GET", detail=False, url_path="admin_vocabulary_get_all", url_name="admin_vocabulary_get_all")
    def admin_vocabulary_get_all(self, request):
        try:
            topic_id = request.query_params.get('topic_id')
            topic = Topic.objects.get(id=topic_id,is_deleted=False)
            serializer = self.serializer_class(topic, context={'request':request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Topic.DoesNotExist:
            return Response({"message": "Topic not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as error:
            print('error: ', error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class TeacherVocabularyViewSet(viewsets.ModelViewSet):
    serializer_class = AdminVocabularySerializers
    permission_classes = [IsAdminUser]  
    @action(methods='GET', detail=True, url_path="admin_vocabulary_get_by_id", url_name="admin_vocabulary_get_by_id")
    def admin_vocabulary_get_by_id(self, request):
        try:
            topic_id = request.query_params.get("vocabulary_id")
            queryset = Vocabulary.objects.get(id=topic_id,is_deleted=False)
            serializer = self.serializer_class(queryset, context={'request':request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Vocabulary.DoesNotExist:
            return Response({"message":"Vocabulary Not Found"},status=status.HTTP_404_NOT_FOUND)
        except Exception as error:
            print("error", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(methods="POST", detail=False, url_path="admin_vocabulary_add", url_name="admin_vocabulary_add")
    def admin_vocabulary_add(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                serializer.save(request=request)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except serializers.ValidationError as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("error", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    
    @action(methods="PATCH", detail=False, url_path="admin_vocabulary_update_by_id", url_name="admin_vocabulary_update_by_id")
    def admin_vocabulary_update_by_id(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                update_model = serializer.update(request=request)
                if update_model is None:
                    return Response({"message": "Vocabulary not found."}, status=status.HTTP_404_NOT_FOUND)
                return Response({"message":"Vocabulary updated successfuly"}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("error", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(methods="DELETE", detail=False, url_path="admin_vocabulary_delete_by_id", url_name="admin_vocabulary_delete_by_id")
    def admin_vocabulary_delete_by_id(self, request):
        try:
            queryset = self.serializer_class()
            delete_model = queryset.delete(request=request)
            if delete_model is None:
                 return Response({"message": "Vocabulary not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response({"message": "Vocabulary  deleted successfully"}, status=status.HTTP_200_OK)  
        except Exception as error:
            print("error", error) 
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        
class TeacherMiniExerciseViewSet(viewsets.ModelViewSet):
    serializer_class = AdminMiniExerciseSerializers
    permission_classes = [IsAdminUser]
    pagination_class = HistoryLogPagination

    @action(methods=["GET"], detail=False, url_path="admin_get_all_fill_in_exercises", url_name="admin_get_all_fill_in_exercises")
    def admin_get_all_fill_in_exercises(self, request):
        try:
            queryset = MiniExercise.objects.filter(exercise_type="T1", is_deleted=False).order_by('id')
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = self.serializer_class(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as error:
            print("admin_get_all_fill_in_exercises_error:", error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(methods=["GET"], detail=False, url_path="admin_get_all_multiple_choice_exercises", url_name="admin_get_all_multiple_choice_exercises")
    def admin_get_all_multiple_choice_exercises(self, request):
        try:
            queryset = MiniExercise.objects.filter(exercise_type="T2", is_deleted=False).order_by('id')
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = self.serializer_class(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as error:
            print("admin_get_all_fill_in_exercises_error:", error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)


# Fill in exercise ===========
class TeacherFillinAnswerExerciseViewSet(viewsets.ModelViewSet):
    serializer_class = AdminFillinAnswerExerciseSerializers
    permission_classes = [IsAdminUser]

    @action(methods=["GET"], detail=True, url_path="admin_get_fill_in_exercise_by_id", url_name="admin_get_fill_in_exercise_by_id")
    def admin_get_fill_in_exercise_by_id(self, request):
        try:
            exercise_id = request.query_params.get('exercise_id')
            exercise = MiniExercise.objects.get(id=exercise_id, exercise_type="T1", is_deleted=False)
            serializer = self.serializer_class(exercise, context={'request':request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except MiniExercise.DoesNotExist:
            return Response({"error": "Fill in exercise not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as error:
            print("admin_get_fill_in_exercise_by_id_error:", error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

class TeacherManageFillinExerciseViewSet(viewsets.ModelViewSet):
    serializer_class = AdminManageFillinExerciseSerializers
    permission_classes = [IsAuthenticated]

    @action(methods=["POST"], detail=False, url_path="admin_fill_in_exercise_add", url_name="admin_fill_in_exercise_add")
    def admin_fill_in_exercise_add(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                serializer.save(request)
                return Response({"message": "Add fill in exercise successfully."}, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("admin_fill_in_exercise_add_error:", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["PATCH"], detail=False, url_path="admin_fill_in_exercise_update_by_id", url_name="admin_fill_in_exercise_update_by_id")
    def admin_fill_in_exercise_update_by_id(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                updated_model = serializer.update(request)
                if updated_model is None:
                    return Response({"message": "Fill in exercise not found."}, status=status.HTTP_404_NOT_FOUND)
                return Response({"message": "Update fill in exercise successfully."}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("admin_fill_in_exercise_update_by_id_error:", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(methods=["DELETE"], detail=False, url_path="admin_fill_in_exercise_delete_by_id", url_name="admin_fill_in_exercise_delete_by_id")
    def admin_fill_in_exercise_delete_by_id(self, request):
        try:
            queryset = self.serializer_class()
            delete_model = queryset.delete(request)
            if delete_model is None:
                return Response({"message": "Fill in exercise not found."}, status=status.HTTP_404_NOT_FOUND)
            return Response({"message": "Delete fill in exercise successfully."}, status=status.HTTP_200_OK)
        except Exception as error:
            print("admin_fill_in_exercise_delete_by_id_error:", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)


# Multiple choices exercise =============
class TeacherMultipleChoicesAnswerExerciseViewSet(viewsets.ModelViewSet):
    serializer_class = AdminMultipleChoicesAnswerExerciseSerializers
    permission_classes = [IsAuthenticated]

    @action(methods=["GET"], detail=True, url_path="admin_get_multiple_choices_exercise_by_id", url_name="admin_get_multiple_choices_exercise_by_id")
    def admin_get_multiple_choices_exercise_by_id(self, request):
        try:
            exercise_id = request.query_params.get('exercise_id')
            exercise = MiniExercise.objects.get(id=exercise_id, exercise_type="T2", is_deleted=False)
            serializer = self.serializer_class(exercise, context={'request':request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except MiniExercise.DoesNotExist:
            return Response({"error": "Multiple choices exercise not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as error:
            print("admin_get_multiple_choices_exercise_by_id_error:", error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

class TeacherManageMultipleChoicesExerciseViewSet(viewsets.ModelViewSet):
    serializer_class = AdminManageMultipleChoicesExerciseSerializers
    permission_classes = [IsAuthenticated]

    @action(methods=["POST"], detail=False, url_path="admin_multiple_choices_exercise_add", url_name="admin_multiple_choices_exercise_add")
    def admin_multiple_choices_exercise_add(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                serializer.save(request)
                return Response({"message": "Add multiple choices exercise successfully."}, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("admin_multiple_choices_exercise_add_error:", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods=["PATCH"], detail=False, url_path="admin_multiple_choices_exercise_update_by_id", url_name="admin_multiple_choices_exercise_update_by_id")
    def admin_multiple_choices_exercise_update_by_id(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                updated_model = serializer.update(request)
                if updated_model is None:
                    return Response({"message": "Multiple choices exercise not found."}, status=status.HTTP_404_NOT_FOUND)
                return Response({"message": "Update multiple choices exercise successfully."}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("admin_multiple_choices_exercise_update_by_id_error:", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(methods=["DELETE"], detail=False, url_path="admin_multiple_choices_exercise_delete_by_id", url_name="admin_multiple_choices_exercise_delete_by_id")
    def admin_multiple_choices_exercise_delete_by_id(self, request):
        try:
            queryset = self.serializer_class()
            delete_model = queryset.delete(request)
            if delete_model is None:
                return Response({"message": "Multiple choices exercise not found."}, status=status.HTTP_404_NOT_FOUND)
            return Response({"message": "Delete multiple choices exercise successfully."}, status=status.HTTP_200_OK)
        except Exception as error:
            print("admin_multiple_choices_exercise_delete_by_id_error:", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)

class TeacherListTopicView(viewsets.ModelViewSet):
    serializer_class = TeacherCourseSerializers
    permission_classes = [IsAdminUser] 
    pagination_class = HistoryLogPagination
    @action(methods=['GET'], detail=False, url_path="topic_admin_get_all", url_name="topic_admin_get_all")
    def topic_admin_get_all(self, request):
        try:
            course_id = request.query_params.get("course_id")
            if not course_id:
                return Response({"message": "Course ID is required."}, status=status.HTTP_400_BAD_REQUEST)

            course = Course.objects.filter(id=course_id, is_deleted=False)
            if not course:
                return Response({"message": "Course Not Found"}, status=status.HTTP_404_NOT_FOUND)  
            page = self.paginate_queryset(course)
            if page is not None:
                serializer = self.get_serializer(page, many=True, context={'request': request})
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(course, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as error:
            print("error:", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class TeacherCourseViewSet(viewsets.ModelViewSet):
    serializer_class = TeacherManageCourseSerializers
    permission_classes = [IsAdminUser] 
    pagination_class = HistoryLogPagination
    
    @action(methods="GET", detail=False, url_path="courses_get_all", url_name="courses_get_all")
    def courses_get_all(self, request):
        try:
            queryset = Course.objects.filter(is_deleted=False).order_by('-update_at')
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True, context={'request': request})
                return self.get_paginated_response(serializer.data)
            serializer = self.serializer_class(queryset, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as error:
            print("error", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    

    @action(methods="POST", detail=False, url_path="course_add", url_name="course_add")
    def course_add(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                serializer.save(request=request)
                return Response({'message':'course added successfuly'}, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except serializers.ValidationError as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("error", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    
    @action(methods="PATCH", detail=False, url_path="course_update_by_id", url_name="course_update_by_id")
    def course_update_by_id(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                update_model = serializer.update(request=request)
                if update_model is None:
                    return Response({"message": "Course not found."}, status=status.HTTP_404_NOT_FOUND)
                return Response({"message":"Course updated successfuly"}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("error", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(methods="DELETE", detail=False, url_path="course_delete_by_id", url_name="course_delete_by_id")
    def course_delete_by_id(self, request):
        try:
            queryset = self.serializer_class()
            delete_model = queryset.delete(request=request)
            if delete_model is None:
                 return Response({"message": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
            return Response({"message": "Course  deleted successfully"}, status=status.HTTP_200_OK)  
        except Exception as error:
            print("error", error) 
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)


class StudentCourseViewSet(viewsets.ModelViewSet):
    serializer_class = StudentCourseSerializers
    permission_classes = [IsAuthenticated] 
    pagination_class = HistoryLogPagination
    @action(methods=["GET"], detail=False, url_path="get_all_course_enrolled", url_name="get_all_course_enrolled")
    def get_all_course_enrolled(self, request):
        try:
            queryset = Course.objects.filter(
                Q(id__in=UserCourseEnrollment.objects.filter(user_id=request.user).values('course_id')),
                is_deleted=False
            )
            
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True, context={'request': request})
                return self.get_paginated_response(serializer.data)
            
            serializer = self.serializer_class(queryset, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as error:
            print("error:", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(methods=["GET"], detail=False, url_path="get_all_course_public", url_name="get_all_course_public")
    def get_all_course_public(self, request):
        try:
            queryset = Course.objects.filter(is_deleted=False,is_public=True)
            page = self.paginate_queryset(queryset)
            if page is not None:
                # Truyền context với request vào serializer
                serializer = self.get_serializer(page, many=True, context={'request': request})
                return self.get_paginated_response(serializer.data)
            # Truyền context với request vào serializer
            serializer = self.serializer_class(queryset, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as error:
            print("error", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    
    
class TeacherEnrollStudentView(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    pagination_class = HistoryLogPagination
    serializer_class = StudentEnrollCourseSerializers
    
    @action(methods="GET", detail=False, url_path="get_all_students_from_course", url_name="get_all_students_from_course")
    def get_all_students_from_course(self, request):
        try:
            course_id = request.query_params.get('course_id')
            if not course_id:
                return Response({"message": "Course ID is required."}, status=status.HTTP_400_BAD_REQUEST)

            enrollments = UserCourseEnrollment.objects.filter(course_id=course_id)
            if not enrollments.exists():
                return Response({"message": "No students enrolled in this course."}, status=status.HTTP_404_NOT_FOUND)

            students = [enrollment.user_id for enrollment in enrollments]
            serializer = StudentSerializer(students, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as error:
            print("Error:", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods="POST", detail=False, url_path="enroll_student", url_name="enroll_student")
    def enroll_student(self, request):
        try:
            serializer = StudentEnrollCourseSerializers(data=request.data)
            if serializer.is_valid():
                results = serializer.enroll(request=request)
                return Response(results, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print('error', error)
            return Response({'message': 'An error occurred on the server', 'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)

    @action(methods="DELETE", detail=False, url_path="delete_student_from_course", url_name="delete_student_from_course")
    def delete_student_from_course(self,request):
        try:
            queryset = StudentEnrollCourseSerializers()
            delete_model = queryset.delete(request=request)
            return Response({"message": "Student  deleted from from course successfully"}, status=status.HTTP_200_OK)  
        except Exception as error:
            print("error", error) 
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)

class SpeechToTextAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        model_directory = "/root/English_Application_API/backend/api/vocabulary/Model3" 
        self.tokenizer = Wav2Vec2Tokenizer.from_pretrained(model_directory)
        self.model = Wav2Vec2ForCTC.from_pretrained(model_directory)
        if torch.cuda.is_available():
            self.model = self.model.to("cuda")  # Đưa mô hình vào GPU

    def post(self, request):
        try:
            serializer = AudioFileSerializer(data=request.data)
            if serializer.is_valid():
                audio_file = serializer.validated_data['file']
                input_audio, _ = librosa.load(audio_file, sr=16000)

                input_values = self.tokenizer(input_audio, return_tensors="pt").input_values
                if torch.cuda.is_available():
                    input_values = input_values.to("cuda")  # Đưa dữ liệu vào GPU

                with torch.no_grad():
                    logits = self.model(input_values).logits
                    predicted_ids = torch.argmax(logits, dim=-1)
                    transcription = self.tokenizer.batch_decode(predicted_ids)[0]

                return Response({"transcription": transcription}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'message':str(e)}, status=status.HTTP_400_BAD_REQUEST)
    

    
class StudentVocabularyNeedReviewView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            vocabularies = UserVocabularyProcess.objects.filter(user_id=request.user, is_need_review=True,is_skipped=False)
            
            vocabularies_list = []
            for process in vocabularies:
                vocabulary = process.vocabulary_id
                serializer = LearnVocabularySerializers(vocabulary)
                
                vocabularies_list.append(serializer.data)
            random_vocabulary_list = random.sample(vocabularies_list, 5) if len(vocabularies_list) >= 5 else vocabularies_list
            vocabularies_data = {
                'total_word': len(vocabularies_list),
                'vocabularies': random_vocabulary_list
            }

            return Response(vocabularies_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
class LeaderBoardView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            course_id = request.query_params.get('course_id')
            time_frame = request.query_params.get('ranking')
            now = timezone.now()
            week = now.isocalendar()[1]
            month = now.month

            if time_frame not in ['0', '1', '2']:
                return Response({'message': 'Invalid ranking parameter. Use "0", "1", or "2".'}, status=status.HTTP_400_BAD_REQUEST)

            if time_frame == '0': 
                leaderboard = LeaderBoard.objects.filter(year_week=week, course=course_id).order_by('-weekly_points')
            elif time_frame == '1': 
                leaderboard = LeaderBoard.objects.filter(year_month=month, course=course_id).order_by('-monthly_points')
            else:
                leaderboard = LeaderBoard.objects.filter(course=course_id).order_by('-total_points')

            leaderboard_data = []
            rank = 1
            for entry in leaderboard:
                points = entry.weekly_points if time_frame == '0' else entry.monthly_points if time_frame == '1' else entry.total_points
                avatar_url = entry.user.user.avatar.url if entry.user.user.avatar else None
                
                if avatar_url:
                    avatar_url = request.build_absolute_uri(avatar_url)
                
                leaderboard_data.append({
                    'id':entry.user.id,
                    'stt': rank,
                    'full_name': entry.user.user.full_name,
                    'avatar': avatar_url,  
                    'points': points,
                    'is_current_user': entry.user.id == request.user.id
                })

                rank += 1

            return Response(leaderboard_data, status=status.HTTP_200_OK)
        
        except Exception as error:
            print('error: ',error)
            return Response({'message': str(error)}, status=status.HTTP_400_BAD_REQUEST)

class StudentPoint(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            student_id = request.query_params.get('student_id')
            student_info = User.objects.get(id=student_id)
            student_point = LeaderBoard.objects.get(user=student_info.id)
            total_vocabulary = UserVocabularyProcess.objects.filter(user_id=student_info.id)
            response = {
                'name':student_info.user.full_name,
                'avatar':request.build_absolute_uri(student_info.user.avatar.url) if student_info.user.avatar else None,
                'points':student_point.total_points,
                'words':total_vocabulary.count()
            }
            return Response(response, status=status.HTTP_200_OK)
        except Exception as error:
            return Response({'message':str(error)}, status=status.HTTP_400_BAD_REQUEST)
        
class StudentProgressView(viewsets.ReadOnlyModelViewSet):
    permission_classes =  [IsAdminUser]
    @action(methods=["GET"], detail=False, url_path="get_list_student", url_name="get_list_student")
    def get_list_student(self, request):
        try:
            course_id = request.query_params.get("course_id")

            if not course_id:
                return Response({'message': 'Course ID is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            topics = Topic.objects.filter(course_id=course_id)

            progress_data = UserTopicProgress.objects.filter(topic_id__in=topics)

            student_progress = {}

            for progress in progress_data:
                student = progress.user_id
                avatar_url = request.build_absolute_uri(student.user.avatar.url) if student.user.avatar else None
                if student.id not in student_progress:
                    student_progress[student.id] = {
                        'id':student.id,
                        'avatar': avatar_url,
                        'student_name': student.user.full_name,
                        'completed_topics': 0,
                        'total_topics': topics.count()
                    }
                if progress.is_completed:
                    student_progress[student.id]['completed_topics'] += 1
            
            progress_list = list(student_progress.values())

            return Response(progress_list, status=status.HTTP_200_OK)

        except Exception as error:
            return Response({'message': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        
    @action(methods=["GET"], detail=False, url_path="student_topics_progress_detail", url_name="student_topics_progress_detail")
    def student_topics_progress_detail(self, request):
        try:
            student_id = request.query_params.get("student_id")

            if not student_id:
                return Response({'message': 'student  id is required'}, status=status.HTTP_400_BAD_REQUEST)

            student = User.objects.get(id=student_id)
            progress_data = UserTopicProgress.objects.filter(user_id=student)

            topics_progress = []

            for progress in progress_data:
                topic = progress.topic_id

                topic_data = {
                    'topic_name': topic.name,
                    'is_completed': progress.is_completed,
                }

                if not progress.is_completed:
                    vocabulary = UserVocabularyProcess.objects.filter(vocabulary_id__topic_id=topic)
                    num_vocabulary = Vocabulary.objects.filter(topic_id=topic)
                    vocab_count = vocabulary.count()
                    total_vocab = num_vocabulary.count()
                    topic_data['completed_vocab'] = vocab_count
                    topic_data['total_vocab'] = total_vocab

                topics_progress.append(topic_data)

            return Response(topics_progress, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({'message': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as error:
            return Response({'message': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        
class GetRandomTenWordsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            vocabularies = list(Vocabulary.objects.all())
            ten_vocab = random.sample(vocabularies,10)
            result = []
            for vocab in ten_vocab:
                result.append({
                    'word':vocab.word,
                    'meaning':vocab.meaning
                })
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            print('error: ', e)
            return Response({'message':str(e)}, status=status.HTTP_400_BAD_REQUEST)