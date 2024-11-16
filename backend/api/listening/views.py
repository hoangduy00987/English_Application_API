from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from django.db.models import Q
from ..submodels.models_listening import *
from .serializers import *
from random import sample


class ListeningPagination(PageNumberPagination):
    page_size = 5
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

class UserListeningTopicMVS(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserListeningTopicSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ListeningPagination

    @action(methods=['GET'], detail=False, url_path='get_all_listening_topic_user', url_name='get_all_listening_topic_user')
    def get_all_listening_topic_user(self, request):
        queryset = ListeningTopic.objects.filter(is_public=True, is_deleted=False).order_by('id')
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.serializer_class(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = self.serializer_class(queryset, many=True, context={'request': request})
        return Response(serializer.data)

class UserListeningExercisesMVS(viewsets.ModelViewSet):
    serializer_class = ListeningExerciseSerializer
    permission_classes = [IsAuthenticated]

    @action(methods=['GET'], detail=False, url_path='user_get_listening_exercises', url_name='user_get_listening_exercises')
    def user_get_listening_exercises(self, request):
        try:
            user = request.user
            topic_id = request.query_params.get('topic_id')
            # Lấy các bài tập chưa hoàn thành
            topic = ListeningTopic.objects.get(pk=topic_id, is_public=True, is_deleted=False)
            exercises = topic.listening_exercises.all()
            done_exercises = UserListeningExerciseResult.objects.filter(
                user=user,
                is_done=True
            ).values_list('listening_exercise', flat=True)
            remaining_exercise = exercises.exclude(id__in=done_exercises)[:1]

            if remaining_exercise:
                serializer = self.serializer_class(remaining_exercise, context={'request': request})
                return Response(serializer.data)
            else:
                topic_progress, _ = UserListeningTopicProgress.objects.get_or_create(
                    user=user,
                    listening_topic=topic
                )
                if not topic_progress.is_completed:
                    topic_progress.is_completed = True
                    topic_progress.save()
            
            exercise_ids = done_exercises.values_list('id', flat=True)
            random_ids = sample(list(exercise_ids), min(len(exercise_ids), 1))
            random_exercises = ListeningExercise.objects.filter(id__in=random_ids).first()

            serializer = self.serializer_class(random_exercises, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ListeningTopic.DoesNotExist:
            return Response({"error": "Topic not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as error:
            print("error_get_listening_exercise_user:", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)

class UpdateListeningExerciseStatusAPIView(APIView):
    serializer_class = UserListeningExerciseManagerSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            exercise_id = request.data.get('exercise_id')
            if not exercise_id:
                return Response({"message": "exercise_id is required."}, status=status.HTTP_400_BAD_REQUEST)
            
            user_exercise_result = UserListeningExerciseResult.objects.filter(
                user=user, listening_exercise_id=exercise_id
            ).first()

            if user_exercise_result:
                user_exercise_result.retries_count += 1
                user_exercise_result.save()
                return Response({"message": "You have finished this exercise again successfully."}, status=status.HTTP_200_OK)
            else:
                serializer = self.serializer_class(data=request.data)
                if serializer.is_valid():
                    serializer.save(request)
                    return Response({"message": "You have finished this exercise successfully."}, status=status.HTTP_200_OK)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("error:", error)
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)
