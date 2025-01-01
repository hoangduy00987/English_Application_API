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
from django.db.models import Q,Count
from django.utils import timezone
from datetime import datetime,timedelta
from django.db.models import Q, Count, F, Func
import torch
from transformers import Wav2Vec2ForCTC, Wav2Vec2Tokenizer
import librosa
from .serializers import AudioFileSerializer
from django.db.models import Sum
import speech_recognition as sr
import calendar


class HistoryLogPagination(PageNumberPagination):
    page_size = 4
    page_size_query_param = 'page_size'
    max_page_size = 30

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

            course = Course.objects.filter(id=course_id, is_deleted=False).order_by('id')
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


    

#Get vocabulary to learn
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

            # Lấy số lượng từ vựng chưa học
            remaining_vocab = vocabulary_list.exclude(id__in=learned_vocab_ids).first()
            remaining_count = vocabulary_list.exclude(id__in=learned_vocab_ids).count()

            # Nếu còn từ vựng chưa học
            if remaining_vocab:
                serializer = self.serializer_class(remaining_vocab, context={'request': request})
                
                if remaining_count == 1:
                    next_topic = Topic.objects.filter(id__gt=topic.id, is_deleted=False, is_public=True).first()
                    if next_topic:
                        next_user_topic, _ = UserTopicProgress.objects.get_or_create(
                            user_id=request.user,
                            topic_id=next_topic
                        )
                        next_user_topic.is_locked = False
                        next_user_topic.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            # Nếu chỉ còn 1 từ vựng chưa học, mở khóa topic tiếp theo
            else:
                
                # Lấy một từ vựng đã học để review
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
            vocabulary_id = Vocabulary.objects.get(id=vocabulary_id)
            if not vocabulary_id:
                return Response({"message": "vocabulary_id is required."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Tìm kiếm hoặc tạo mới từ vựng
            user_vocab_process, created = UserVocabularyProcess.objects.get_or_create(
                user_id=request.user,
                vocabulary_id=vocabulary_id,
                defaults={
                    "review_count": 1,
                    "is_need_review": False,
                    "is_learned": True,
                    "last_learned_at": timezone.now(),
                }
            )

            if not created:  # Nếu từ vựng đã tồn tại
                user_vocab_process.review_count = (user_vocab_process.review_count or 0) + 1
                user_vocab_process.is_need_review = False
                user_vocab_process.is_learned = True
                user_vocab_process.last_learned_at = timezone.now()
                user_vocab_process.save()
            topic_id = user_vocab_process.vocabulary_id.topic_id
            total_vocab_count = Vocabulary.objects.filter(topic_id=topic_id).count()
            
            learned_vocab_count = UserVocabularyProcess.objects.filter(
                user_id=request.user, 
                vocabulary_id__topic_id=topic_id, 
                is_learned=True
            ).count()
            print(learned_vocab_count)
            if learned_vocab_count == total_vocab_count:
                user_topic_process, created = UserTopicProgress.objects.get_or_create(
                    user_id=request.user,
                    topic_id=topic_id
                )
            user_topic_process.is_completed = True
            user_topic_process.save()
            update_leader_board(request.user, 5, user_vocab_process.vocabulary_id.topic_id.course_id.id)
            return Response({'message': 'You have finished reviewing this word.'}, status=status.HTTP_200_OK)

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


# List learned vocabularies of user
class ListLearnedVocabularyOfUserMVS(viewsets.ReadOnlyModelViewSet):
    serializer_class = ListLearnedVocabularyOfUserSerializers
    permission_classes = [IsAuthenticated]
    pagination_class = HistoryLogPagination

    @action(methods=['GET'], detail=False, url_path='get_all_learned_vocabulary', url_name='get_all_learned_vocabulary')
    def get_all_learned_vocabulary(self, request):
        try:
            queryset = UserVocabularyProcess.objects.filter(user_id=request.user).order_by('-id')
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.serializer_class(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.serializer_class(queryset, many=True)
            return Response(serializer.data)
        except Exception as error:
            print("get_all_learned_vocabulary_error:", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)


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

            course = Course.objects.filter(id=course_id, is_deleted=False).order_by('id')
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
            name = request.query_params.get('name')
            queryset = Course.objects.filter(is_deleted=False).order_by('-update_at')
            if name:
                queryset = queryset.filter(name__icontains=name)
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
            ).order_by('-id')
            
            name = request.query_params.get('name')
            if name:
                queryset = queryset.filter(name__icontains=name)
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
            queryset = Course.objects.filter(
                ~Q(id__in=UserCourseEnrollment.objects.filter(user_id=request.user).values('course_id')) &
                Q(is_deleted=False) &
                Q(is_public=True)
            ).order_by('-id')
            name = request.query_params.get('name')
            if name:
                queryset = queryset.filter(name__icontains=name)
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

class StudentEnrollCourseView(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    @action(methods="POST", detail=False, url_path="student_enroll_course", url_name="student_enroll_course")
    def student_enroll_course(self, request):
        try:
            user_id = request.user
            course_id = request.data.get('course_id')
            course = Course.objects.get(id=course_id)
            UserCourseEnrollment.objects.create(user_id=user_id,course_id=course, enrolled_at=timezone.now())
            return Response({'message':'student enrolled course successfuly'}, status=status.HTTP_200_OK)
        except Exception as error:
            print('error', error)
            return Response({'message': 'An error occurred on the server', 'detail': str(error)}, status=status.HTTP_400_BAD_REQUEST)
    
class TeacherEnrollStudentView(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    pagination_class = HistoryLogPagination
    serializer_class = StudentEnrollCourseSerializers
    
    @action(methods="GET", detail=False, url_path="get_all_students_from_course", url_name="get_all_students_from_course")
    def get_all_students_from_course(self, request):
        try:
            # Lấy course_id từ query parameters
            course_id = request.query_params.get('course_id')
            if not course_id:
                return Response({"message": "Course ID is required."}, status=status.HTTP_400_BAD_REQUEST)

            enrollments = UserCourseEnrollment.objects.filter(course_id=course_id)
            if not enrollments.exists():
                return Response({"message": "No students enrolled in this course."}, status=status.HTTP_404_NOT_FOUND)

            # Loại bỏ trùng lặp user_id bằng set
            student_ids = set(enrollments.values_list('user_id', flat=True))

            # Lấy thông tin chi tiết sinh viên
            students = User.objects.filter(id__in=student_ids)
            if not students.exists():
                return Response({"message": "No students found."}, status=status.HTTP_404_NOT_FOUND)

            serializer = StudentSerializer(students, many=True, context={"course_id": course_id})
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as error:
            print("Error:", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
    def post(self, request, *args, **kwargs):
        serializer = AudioFileSerializer(data=request.data)
        if serializer.is_valid():
            audio_file = serializer.validated_data['audio_file']
            
            # Sử dụng SpeechRecognition để xử lý
            recognizer = sr.Recognizer()
            try:
                # Đọc file âm thanh
                with sr.AudioFile(audio_file) as source:
                    audio_data = recognizer.record(source)
                
                # Chuyển đổi âm thanh sang văn bản
                text = recognizer.recognize_sphinx(audio_data)

                # Trả về kết quả
                return Response({"text": text}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    
class StudentVocabularyNeedReviewView(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    @action(methods=["GET"], detail=False, url_path="get_courses_need_review", url_name="get_courses_need_review")
    def get_courses_need_review(self, request):
        try:
            name = request.query_params.get('name')
            course_need_review = UserCourseEnrollment.objects.filter(user_id=request.user)
            if name:
                course_need_review = course_need_review.filter(course_id__name__icontains=name)
            response_data = []
            for enrollment in course_need_review:
                course = enrollment.course_id
                vocabularies = UserVocabularyProcess.objects.filter(
                    user_id=request.user,
                    vocabulary_id__topic_id__course_id=course, 
                    is_need_review=True,
                    is_skipped=False)
                response_data.append({
                    'course_id':course.id,
                    'course_image': request.build_absolute_uri(course.image.url),
                    'name_course': course.name,
                    'total_word': len(vocabularies)
                })

            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(methods=["GET"], detail=False, url_path="get_vocabularies_need_review", url_name="get_vocabularies_need_review")
    def get_vocabularies_need_review(self, request):
        try:

            course_id = request.query_params.get('course_id')
            if not course_id:
                return Response({'message':'course_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            course = Course.objects.get(id=course_id)
            response_data = []
            vocabularies = UserVocabularyProcess.objects.filter(
                    user_id=request.user,
                    vocabulary_id__topic_id__course_id=course, 
                    is_need_review=True,
                    is_skipped=False)
                
                
            vocabularies_list = [
                    ReviewVocabularySerializers(process.vocabulary_id,context={"request": request}).data
                    for process in vocabularies
            ]
            random_vocabulary_list = (
                random.sample(vocabularies_list, 5) if len(vocabularies_list) >= 5 else vocabularies_list
            )
            response_data.append({
                    'vocabularies': random_vocabulary_list,
                })

            return Response(response_data, status=status.HTTP_200_OK)
        
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
            if not student_id:
                return Response({'message':'student_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            student_info = User.objects.get(id=student_id)
            total_points = LeaderBoard.objects.filter(user=student_info.id).aggregate(Sum('total_points'))['total_points__sum'] or 0
            total_vocabulary = UserVocabularyProcess.objects.filter(user_id=student_info.id)
            response = {
                'name':student_info.user.full_name,
                'avatar':request.build_absolute_uri(student_info.user.avatar.url) if student_info.user.avatar else None,
                'points':total_points,
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
            
            topics = Topic.objects.filter(course_id=course_id,is_deleted=False,is_public=True)

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
            course_id = request.query_params.get("course_id")
            if not student_id:
                return Response({'message': 'student id is required'}, status=status.HTTP_400_BAD_REQUEST)
            if not course_id:
                return Response({'message': 'course id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            student = User.objects.get(id=student_id)
            course = Course.objects.get(id=course_id)
            progress_data = UserTopicProgress.objects.filter(user_id=student, topic_id__course_id=course)

            response_data = {
                "student_name": student.user.full_name,
                "avatar": request.build_absolute_uri(student.user.avatar),
                "list_topic": []
            }

            for progress in progress_data:
                topic = progress.topic_id

                topic_data = {
                    'student_name': student.user.full_name,
                    'topic_name': topic.name,
                    'image': request.build_absolute_uri(topic.image.url) if topic.image else None,
                    'is_completed': progress.is_completed,
                }

                if not progress.is_completed:
                    vocabulary = UserVocabularyProcess.objects.filter(vocabulary_id__topic_id=topic)
                    num_vocabulary = Vocabulary.objects.filter(topic_id=topic)
                    vocab_count = vocabulary.count()
                    total_vocab = num_vocabulary.count()
                    topic_data['completed_vocab'] = vocab_count
                    topic_data['total_vocab'] = total_vocab
                
                response_data['list_topic'].append(topic_data)

            return Response(response_data, status=status.HTTP_200_OK)

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

class GetRandomWordsInReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            word = request.query_params.get('word')
            vocabularies = list(Vocabulary.objects.exclude(word=word))
            three_vocab = random.sample(vocabularies, 3)
            result = []
            for vocab in three_vocab:
                result.append({'word': vocab.word})
            result.append({'word': word})
            result = random.sample(result, 4)
            return Response(result)
        except Exception as error:
            print("get_random_word_in_review_error:", error)
            return Response({'message': str(error)}, status=status.HTTP_400_BAD_REQUEST)

class TopCoursesView(APIView):
    def get(self, request):
        try:
            top_courses = Course.objects.annotate(
                user_count=Count('usercourseenrollment__user_id', distinct=True),
                vocabulary_count=Count('topic__vocabularies', filter=Q(topic__vocabularies__is_deleted=False), distinct=True)
            ).order_by('-user_count')[:5]

            response_data = []
            for course in top_courses:
                data = {
                    'name': course.name,
                    'image': request.build_absolute_uri(course.image.url) if course.image else None,
                    'total_students': course.user_count,
                    'total_vocabularies': course.vocabulary_count
                }
                response_data.append(data)
            
            return Response(response_data)
        except Exception as error:
            print("error:", error)
            return Response({"error": str(error)}, status=status.HTTP_400_BAD_REQUEST)

class ExtractMonth(Func):
    function = 'EXTRACT'
    template = '%(function)s(MONTH FROM %(expressions)s)'

class AdminDashboardMVS(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]

    @action(methods=["GET"], detail=False, url_path="statistics_dashboard", url_name="statistics_dashboard")
    def statistics_dashboard(self, request):
        courses_count = Course.objects.filter(is_deleted=False)
        private_count = courses_count.filter(is_public=False).count()
        public_count = courses_count.filter(is_public=True).count()
        students_count = UserCourseEnrollment.objects.all().distinct("user_id").count()
        vocabularies_count = Vocabulary.objects.filter(is_deleted=False).count()
        data = {}
        data["private_courses"] = private_count
        data["public_courses"] = public_count
        data["students"] = students_count
        data["vocabularies"] = vocabularies_count
        
        return Response(data)
    
    @action(methods=["GET"], detail=False, url_path="line_chart", url_name="line_chart")
    def line_chart(self, request):
        year = request.query_params.get('year')
        current_time = timezone.localtime(timezone.now()).date()
        year = int(year) if year else current_time.year
        
        prev_count = UserCourseEnrollment.objects \
            .filter(enrolled_at__year__lt=year) \
            .distinct('user_id').count()
        query = UserCourseEnrollment.objects.filter(enrolled_at__year=year) \
            .annotate(month=ExtractMonth('enrolled_at')) \
            .values('month') \
            .annotate(user_count=Count('user_id'))

        data = {entry['month']: entry['user_count'] for entry in query}

        result = []
        cumulative_count = prev_count
        for month in range(1, 13):
            monthly_count = data.get(month, 0)
            cumulative_count += monthly_count
            result.append({
                "month": month,
                "students_count": cumulative_count
            })

        return Response(result)
    
    @action(methods=["GET"], detail=False, url_path="pie_chart", url_name="pie_chart")
    def pie_chart(self, request):
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        current_time = timezone.localtime(timezone.now()).date()
        month = int(month) if month else current_time.month
        year = int(year) if year else current_time.year
        last_day = calendar.monthrange(year, month)[1]
        last_date = timezone.datetime(year, month, last_day)

        query = UserCourseEnrollment.objects \
            .filter(enrolled_at__lte=last_date) \
            .annotate(name_course=F('course_id__name')) \
            .values('name_course') \
            .annotate(user_count=Count('user_id')) \
            .order_by('name_course')
        
        data = {}
        data["month"] = month
        data["year"] = year
        result = [
            {
                "name_course": entry['name_course'],
                "students_count": entry['user_count']
            }
            for entry in query
        ]
        data["result"] = result

        return Response(data)
