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
from datetime import datetime
from django.db.models import Q
import torch
from transformers import Wav2Vec2ForCTC, Wav2Vec2Tokenizer
import librosa
from .serializers import AudioFileSerializer



class HistoryLogPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

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


# get all topic
class UserTopicViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = HistoryLogPagination

    @action(methods=['GET'], detail=False, url_path="topic_user_get_all", url_name="topic_user_get_all")
    def topic_user_get_all(self, request):
        try:
            course_id = request.query_params.get("course_id")
            if not course_id:
                return Response({"message": "Course ID is required."}, status=status.HTTP_400_BAD_REQUEST)

            course = Course.objects.get(id=course_id, is_deleted=False)
            is_teacher = course.teacher_id.id == request.user.id
            if is_teacher:
                serializer = TeacherCourseSerializers(course, context={'request': request})
            else:
                serializer = UserCourseSerializers(course, context={'request': request})

            return Response({
                "is_teacher": is_teacher,
                "topics": serializer.data
                
            }, status=status.HTTP_200_OK)

        except Course.DoesNotExist:
            return Response({"message": "Course Not Found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as error:
            print("error:", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)


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
                next_topic = Topic.objects.filter(order__gt=topic.order,
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
                # update review_count
                user_vocab_process.review_count = (user_vocab_process.review_count or 0) + 1
                user_vocab_process.save()
                return Response({'message':'You have finished reviewing this word.'}, status=status.HTTP_200_OK)
            else:
                # if none, create new record
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

#get all vocabulary of topic
class UserListVocabularyViewSet(APIView):
    serializer_class = UserListVocabularyOfTopicSerializers
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            topic_id = request.query_params.get('topic_id')
            topic = Topic.objects.get(id=topic_id, is_public=True, is_deleted=False)
            serializer = self.serializer_class(topic, context={'request':request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Topic.DoesNotExist:
            return Response({"message": "Topic Not Found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as error:
            print('error: ', error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)
        

class ReviewVocabularyViewSet(APIView):
    serializer_class = VocabularyNeedReviewSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            queryset = UserVocabularyProcess.objects.filter(user_id=request.user, is_need_review=True)

            if not queryset.exists():
                return Response({"detail": "No vocabulary found for review."}, status=status.HTTP_404_NOT_FOUND)
            
            serializer = self.serializer_class(queryset, many=True)
        
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    

#============Admin==========
class AdminManageTopicViewset(viewsets.ModelViewSet):
    serializer_class = AdminTopicSerializers
    pagination_class = HistoryLogPagination
    permission_classes = [IsAuthenticated]

    @action(methods=["GET"], detail=False, url_path="admin_topic_get_all", url_name="admin_topic_get_all")
    def admin_topic_get_all(self, request):
        try:
            queryset = Topic.objects.filter(is_deleted=False).order_by("order")
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = self.serializer_class(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as error:
            print("error", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)
    
   
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

class AdminListVocabularyViewSet(viewsets.ModelViewSet):
    serializer_class = AdminVocabularyOfTopicSerializers
    permission_classes = [IsAuthenticated]

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


class AdminVocabularyViewSet(viewsets.ModelViewSet):
    serializer_class = AdminVocabularySerializers
    permission_classes = [IsAuthenticated]  
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
        
class AdminMiniExerciseViewSet(viewsets.ModelViewSet):
    serializer_class = AdminMiniExerciseSerializers
    permission_classes = [IsAuthenticated]
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
class AdminFillinAnswerExerciseViewSet(viewsets.ModelViewSet):
    serializer_class = AdminFillinAnswerExerciseSerializers
    permission_classes = [IsAuthenticated]

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

class AdminManageFillinExerciseViewSet(viewsets.ModelViewSet):
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
class AdminMultipleChoicesAnswerExerciseViewSet(viewsets.ModelViewSet):
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

class AdminManageMultipleChoicesExerciseViewSet(viewsets.ModelViewSet):
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

class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSerializers
    permission_classes = [IsAuthenticated] 
        
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
    
    @action(methods=["GET"], detail=False, url_path="get_all_my_course_and_enrolled", url_name="get_all_my_course_and_enrolled")
    def get_all_my_course_and_enrolled(self, request):
        try:
            queryset = Course.objects.filter(
                Q(teacher_id=request.user) | 
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

class UserEnrollCourseView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self,request):
        try:
            serializer = StudentEnrollCourseSerializers(data=request.data)
            if serializer.is_valid():
                serializer.enroll(request=request)
                return Response({'message':'students added successfuly'},status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print('error',error)
            return Response({'message':'An error occurred on the server', 'detail':str(error)},status=status.HTTP_400_BAD_REQUEST)


class SpeechToTextAPIView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        model_directory = "./vocabulary/Model3" 
        self.tokenizer = Wav2Vec2Tokenizer.from_pretrained(model_directory)
        self.model = Wav2Vec2ForCTC.from_pretrained(model_directory)
        if torch.cuda.is_available():
            self.model = self.model.to("cuda")  # Đưa mô hình vào GPU

    def post(self, request):
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