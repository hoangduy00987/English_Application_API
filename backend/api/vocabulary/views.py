from rest_framework.response import Response
from rest_framework import status,viewsets
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
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

class HistoryLogPagination(PageNumberPagination):
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

# get all topic
class UserTopicViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TopicSerializers
    pagination_class = HistoryLogPagination

    @action(methods='GET', detail=False, url_path="topic_user_get_all", url_name="topic_user_get_all")
    def topic_user_get_all(self, request):
        try:
            topic = Topic.objects.filter(is_deleted=False, is_public=True).order_by("order")
            page = self.paginate_queryset(topic)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            serializer = self.get_serializer(topic, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as error:
            print('error: ', error)
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
            vocabulary_list = topic.vocabularies.filter(is_deleted=False).order_by('order')
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
                if next_topic:
                    next_topic.is_locked=False
                    next_topic.save()

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
    @action(methods='GET', detail=False, url_path="user_learn_vocabulary_get", url_name="user_learn_vocabulary_get")
    def user_learn_vocabulary_post(self, request):
        try:
            serializer = self.serializer_class(data=request.data)
            if serializer.is_valid():
                serializer.save(request=request)
                return Response({'message':'You have finished studying this word'}, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as error:
            print("error", error) 
            return Response({"message": "An error occurred on the server.", "details": str(error)}, status=status.HTTP_400_BAD_REQUEST)

#get all vocabulary of topic
class ListVocabularyViewSet(APIView):
    serializer_class = ListVocabularyOfTopicSerializers
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