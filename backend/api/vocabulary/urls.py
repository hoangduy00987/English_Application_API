
from django.urls import path,include
from .views import *

#Course
course_get_by_id = CourseViewSet.as_view(
    {'get':'course_get_by_id'}
)
course_add = CourseViewSet.as_view(
    {'post':'course_add'}
)
course_update_by_id = CourseViewSet.as_view(
    {'patch':'course_update_by_id'}
)
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
#MiniExercise
admin_get_all_fill_in_exercises = AdminMiniExerciseViewSet.as_view(
    {'get':'admin_get_all_fill_in_exercises'}
)
admin_get_fill_in_exercise_by_id = AdminFillinAnswerExerciseViewSet.as_view(
    {'get':'admin_get_fill_in_exercise_by_id'}
)
admin_fill_in_exercise_add = AdminManageFillinExerciseViewSet.as_view(
    {'post':'admin_fill_in_exercise_add'}
)
admin_fill_in_exercise_update_by_id = AdminManageFillinExerciseViewSet.as_view(
    {'patch':'admin_fill_in_exercise_update_by_id'}
)
admin_fill_in_exercise_delete_by_id = AdminManageFillinExerciseViewSet.as_view(
    {'delete':'admin_fill_in_exercise_delete_by_id'}
)
admin_get_all_multiple_choice_exercises = AdminMiniExerciseViewSet.as_view(
    {'get':'admin_get_all_multiple_choice_exercises'}
)
admin_get_multiple_choices_exercise_by_id = AdminMultipleChoicesAnswerExerciseViewSet.as_view(
    {'get':'admin_get_multiple_choices_exercise_by_id'}
)
admin_multiple_choices_exercise_add = AdminManageMultipleChoicesExerciseViewSet.as_view(
    {'post':'admin_multiple_choices_exercise_add'}
)
admin_multiple_choices_exercise_update_by_id = AdminManageMultipleChoicesExerciseViewSet.as_view(
    {'patch':'admin_multiple_choices_exercise_update_by_id'}
)
admin_multiple_choices_exercise_delete_by_id = AdminManageMultipleChoicesExerciseViewSet.as_view(
    {'delete':'admin_multiple_choices_exercise_delete_by_id'}
)

urlpatterns = [
    #Course
    path('course_get_by_id/', course_get_by_id, name='course_get_by_id'),
    path('course_get_by_id/', course_get_by_id, name='course_get_by_id'),
    # Topic
    path('topic_user_get_all/', topic_user_get_all, name='topic_user_get_all'),
    path('admin_topic_get_all/', admin_topic_get_all, name='admin_topic_get_all'),
    path('admin_topic_get_by_id/', admin_topic_get_by_id, name='admin_topic_get_by_id'),
    path('admin_topic_add/', admin_topic_add, name='admin_topic_add'),
    path('admin_topic_update_by_id/', admin_topic_update_by_id, name='admin_topic_update_by_id'),
    path('admin_topic_delete_by_id/', admin_topic_delete_by_id, name='admin_topic_delete_by_id'),
    #Vocabulary
    path('user_learn_vocabulary_get/', user_learn_vocabulary_get, name='user_learn_vocabulary_get'),
    path('user_learn_vocabulary_post/', user_learn_vocabulary_post, name='user_learn_vocabulary_post'),
    path('vocabulary_get_all/', UserListVocabularyViewSet.as_view(), name="vocabulary_get_all"),
    path('vocabulary_need_review_get_all/', ReviewVocabularyViewSet.as_view(), name="vocabulary_need_review_get_all"),
    path('admin_vocabulary_add/', admin_vocabulary_add, name='admin_vocabulary_add'),
    path('admin_vocabulary_update_by_id/', admin_vocabulary_update_by_id, name='admin_vocabulary_update_by_id'),
    path('admin_vocabulary_delete_by_id/', admin_vocabulary_delete_by_id, name='admin_vocabulary_delete_by_id'),

    path('set_next_review/', set_next_review, name='set_next_review'),
    path('user_vocab_process/', user_vocab_process, name='user_vocab_process'),
    #Admin Vocabulary
    path('admin_vocabulary_get_all/', admin_vocabulary_get_all, name='admin_vocabulary_get_all'),
    path('admin_vocabulary_get_by_id/', admin_vocabulary_get_by_id, name='admin_vocabulary_get_by_id'),
    
    #Admin MiniExercise
    path('admin_get_all_fill_in_exercises/', admin_get_all_fill_in_exercises, name='admin_get_all_fill_in_exercises'),
    path('admin_get_fill_in_exercise_by_id/', admin_get_fill_in_exercise_by_id, name='admin_get_fill_in_exercise_by_id'),
    path('admin_fill_in_exercise_add/', admin_fill_in_exercise_add, name='admin_fill_in_exercise_add'),
    path('admin_fill_in_exercise_update_by_id/', admin_fill_in_exercise_update_by_id, name='admin_fill_in_exercise_update_by_id'),
    path('admin_fill_in_exercise_delete_by_id/', admin_fill_in_exercise_delete_by_id, name='admin_fill_in_exercise_delete_by_id'),
    path('admin_get_all_multiple_choice_exercises/', admin_get_all_multiple_choice_exercises, name='admin_get_all_multiple_choice_exercises'),
    path('admin_get_multiple_choices_exercise_by_id/', admin_get_multiple_choices_exercise_by_id, name='admin_get_multiple_choices_exercise_by_id'),
    path('admin_multiple_choices_exercise_add/', admin_multiple_choices_exercise_add, name='admin_multiple_choices_exercise_add'),
    path('admin_multiple_choices_exercise_update_by_id/', admin_multiple_choices_exercise_update_by_id, name='admin_multiple_choices_exercise_update_by_id'),
    path('admin_multiple_choices_exercise_delete_by_id/', admin_multiple_choices_exercise_delete_by_id, name='admin_multiple_choices_exercise_delete_by_id'),
]
