
from django.urls import path,include
from .views import *

topic_user_get_all = UserTopicViewSet.as_view(
    {'get':'topic_user_get_all'}
)
user_learn_vocabulary_get = UserVocabularyViewSet.as_view(
    {'get':'user_learn_vocabulary_get'}
)
user_learn_vocabulary_post = UserVocabularyProcessViewSet.as_view(
    {'get':'user_learn_vocabulary_post'}
)
urlpatterns = [
    # Topic
    path('topic_user_get_all/', topic_user_get_all),
    path('user_learn_vocabulary_get/', user_learn_vocabulary_get),
    path('user_learn_vocabulary_post/', user_learn_vocabulary_post),
    path('vocabulary_get_all/', ListVocabularyViewSet.as_view(), name="vocabulary_get_all"),

]
