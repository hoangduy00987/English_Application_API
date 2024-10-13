
from django.urls import path,include
from .views import *

#Topic
topic_user_get_all = UserTopicViewSet.as_view(
    {'get':'topic_user_get_all'}
)
admin_topic_get_all = AdminManageTopicViewset.as_view(
    {'get':'admin_topic_get_all'}
)
admin_topic_get_by_id = AdminManageTopicViewset.as_view(
    {'get':'admin_topic_get_by_id'}
)
admin_topic_add = AdminManageTopicViewset.as_view(
    {'post':'admin_topic_add'}
)
admin_topic_update_by_id = AdminManageTopicViewset.as_view(
    {'patch':'admin_topic_update_by_id'}
)
admin_topic_delete_by_id = AdminManageTopicViewset.as_view(
    {'delete':'admin_topic_delete_by_id'}
)
#Vocabulary
user_learn_vocabulary_get = UserVocabularyViewSet.as_view(
    {'get':'user_learn_vocabulary_get'}
)

admin_vocabulary_get_all = AdminListVocabularyViewSet.as_view(
    {'get':'admin_vocabulary_get_all'}
)
admin_vocabulary_get_by_id = AdminVocabularyViewSet.as_view(
    {'get':'admin_vocabulary_get_by_id'}
)
admin_vocabulary_add = AdminVocabularyViewSet.as_view(
    {'post':'admin_vocabulary_add'}
)
admin_vocabulary_update_by_id = AdminVocabularyViewSet.as_view(
    {'patch':'admin_vocabulary_update_by_id'}
)
admin_vocabulary_delete_by_id = AdminVocabularyViewSet.as_view(
    {'delete':'admin_vocabulary_delete_by_id'}
)
#UserVocabularyProcess
user_learn_vocabulary_post = UserVocabularyProcessViewSet.as_view(
    {'post':'user_learn_vocabulary_post'}
)

set_next_review = UserVocabularyProcessViewSet.as_view(
    {'post':'set_next_review'}
)
user_vocab_process = UserVocabularyProcessViewSet.as_view(
    {'get':'user_vocab_process'}
)

urlpatterns = [
    # Topic
    path('topic_user_get_all/', topic_user_get_all),
    path('admin_topic_get_all/', admin_topic_get_all),
    path('admin_topic_get_by_id/', admin_topic_get_by_id),
    path('admin_topic_add/', admin_topic_add),
    path('admin_topic_update_by_id/', admin_topic_update_by_id),
    path('admin_topic_delete_by_id/', admin_topic_delete_by_id),
    #Vocabulary
    path('user_learn_vocabulary_get/', user_learn_vocabulary_get),
    path('user_learn_vocabulary_post/', user_learn_vocabulary_post),
    path('vocabulary_get_all/', UserListVocabularyViewSet.as_view(), name="vocabulary_get_all"),
    path('vocabulary_need_review_get_all/', ReviewVocabularyViewSet.as_view(), name="vocabulary_need_review_get_all"),
    path('admin_vocabulary_add/', admin_vocabulary_add),
    path('admin_vocabulary_update_by_id/', admin_vocabulary_update_by_id),
    path('admin_vocabulary_delete_by_id/', admin_vocabulary_delete_by_id),

    path('set_next_review/', set_next_review),
    path('user_vocab_process/', user_vocab_process),
    #Admin Vocabulary
    path('admin_vocabulary_get_all/', admin_vocabulary_get_all),
    path('admin_vocabulary_get_by_id/', admin_vocabulary_get_by_id),
    
]
