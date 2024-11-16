from django.urls import path
from .views import *

get_all_listening_topic_user = UserListeningTopicMVS.as_view({
    'get': 'get_all_listening_topic_user'
})
user_get_listening_exercises = UserListeningExercisesMVS.as_view({
    'get': 'user_get_listening_exercises'
})

urlpatterns = [
    path('get_all_listening_topic_user/', get_all_listening_topic_user, name='get_all_listening_topic_user'),
    path('listening_exercises_user_get/', user_get_listening_exercises, name='user_get_listening_exercises'),
    path('listening_exercises_user_post/', UpdateListeningExerciseStatusAPIView.as_view(), name='listening_exercises_user_post'),
]
