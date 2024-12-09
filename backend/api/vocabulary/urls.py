
from django.urls import path,include
from .views import *

#Course

get_all_course_enrolled = StudentCourseViewSet.as_view(
    {'get':'get_all_course_enrolled'}
)
get_all_course_public = StudentCourseViewSet.as_view(
    {'get':'get_all_course_public'}
)
course_add = TeacherCourseViewSet.as_view(
    {'post':'course_add'}
)
course_update_by_id = TeacherCourseViewSet.as_view(
    {'patch':'course_update_by_id'}
)
course_delete_by_id = TeacherCourseViewSet.as_view(
    {'delete':'course_delete_by_id'}
)
#Topic
topic_user_get_all = StudentTopicViewSet.as_view(
    {'get':'topic_user_get_all'}
)
topic_admin_get_all = TeacherListTopicView.as_view(
    {'get':'topic_admin_get_all'}
)
admin_topic_get_by_id = TeacherManageTopicViewset.as_view(
    {'get':'admin_topic_get_by_id'}
)
admin_topic_add = TeacherManageTopicViewset.as_view(
    {'post':'admin_topic_add'}
)
admin_topic_update_by_id = TeacherManageTopicViewset.as_view(
    {'patch':'admin_topic_update_by_id'}
)
admin_topic_delete_by_id = TeacherManageTopicViewset.as_view(
    {'delete':'admin_topic_delete_by_id'}
)
#Vocabulary
user_learn_vocabulary_get = UserVocabularyViewSet.as_view(
    {'get':'user_learn_vocabulary_get'}
)

admin_vocabulary_get_all = TeacherListVocabularyViewSet.as_view(
    {'get':'admin_vocabulary_get_all'}
)
admin_vocabulary_get_by_id = TeacherVocabularyViewSet.as_view(
    {'get':'admin_vocabulary_get_by_id'}
)
admin_vocabulary_add = TeacherVocabularyViewSet.as_view(
    {'post':'admin_vocabulary_add'}
)
admin_vocabulary_update_by_id = TeacherVocabularyViewSet.as_view(
    {'patch':'admin_vocabulary_update_by_id'}
)
admin_vocabulary_delete_by_id = TeacherVocabularyViewSet.as_view(
    {'delete':'admin_vocabulary_delete_by_id'}
)
#UserVocabularyProcess
user_learn_vocabulary_post = UserVocabularyProcessViewSet.as_view(
    {'post':'user_learn_vocabulary_post'}
)
user_skip_vocabulary = UserVocabularyProcessViewSet.as_view(
    {'post':'user_skip_vocabulary'}
)
set_next_review = UserVocabularyProcessViewSet.as_view(
    {'post':'set_next_review'}
)
user_vocab_process = UserVocabularyProcessViewSet.as_view(
    {'get':'user_vocab_process'}
)
get_all_learned_vocabulary = ListLearnedVocabularyOfUserMVS.as_view(
    {'get': 'get_all_learned_vocabulary'}
)
#MiniExercise
admin_get_all_fill_in_exercises = TeacherMiniExerciseViewSet.as_view(
    {'get':'admin_get_all_fill_in_exercises'}
)
admin_get_fill_in_exercise_by_id = TeacherFillinAnswerExerciseViewSet.as_view(
    {'get':'admin_get_fill_in_exercise_by_id'}
)
admin_fill_in_exercise_add = TeacherManageFillinExerciseViewSet.as_view(
    {'post':'admin_fill_in_exercise_add'}
)
admin_fill_in_exercise_update_by_id = TeacherManageFillinExerciseViewSet.as_view(
    {'patch':'admin_fill_in_exercise_update_by_id'}
)
admin_fill_in_exercise_delete_by_id = TeacherManageFillinExerciseViewSet.as_view(
    {'delete':'admin_fill_in_exercise_delete_by_id'}
)
admin_get_all_multiple_choice_exercises = TeacherMiniExerciseViewSet.as_view(
    {'get':'admin_get_all_multiple_choice_exercises'}
)
admin_get_multiple_choices_exercise_by_id = TeacherMultipleChoicesAnswerExerciseViewSet.as_view(
    {'get':'admin_get_multiple_choices_exercise_by_id'}
)
admin_multiple_choices_exercise_add = TeacherManageMultipleChoicesExerciseViewSet.as_view(
    {'post':'admin_multiple_choices_exercise_add'}
)
admin_multiple_choices_exercise_update_by_id = TeacherManageMultipleChoicesExerciseViewSet.as_view(
    {'patch':'admin_multiple_choices_exercise_update_by_id'}
)
admin_multiple_choices_exercise_delete_by_id = TeacherManageMultipleChoicesExerciseViewSet.as_view(
    {'delete':'admin_multiple_choices_exercise_delete_by_id'}
)
#AdminFunction
courses_get_all = TeacherCourseViewSet.as_view(
    {'get':'courses_get_all'}
)
#enroll student
 
enroll_student = TeacherEnrollStudentView.as_view(
    {'post':'enroll_student'}
)
delete_student_from_course = TeacherEnrollStudentView.as_view(
    {'delete':'delete_student_from_course'}
)
get_all_students_from_course = TeacherEnrollStudentView.as_view(
    {'get':'get_all_students_from_course'}
)

#student enroll course
student_enroll_course = StudentEnrollCourseView.as_view(
    {'post':'student_enroll_course'}
)

#StudentProgress
get_list_student = StudentProgressView.as_view(
    {'get':'get_list_student'}
)
student_topics_progress_detail = StudentProgressView.as_view(
    {'get':'student_topics_progress_detail'}
)
# vocabulary need review
get_courses_need_review = StudentVocabularyNeedReviewView.as_view(
    {'get':'get_courses_need_review'}
)
get_vocabularies_need_review = StudentVocabularyNeedReviewView.as_view(
    {'get':'get_vocabularies_need_review'}
)

urlpatterns = [
    #Adminfunction
    path('courses_get_all/', courses_get_all, name='courses_get_all'),
    #Course
    path('get_all_course_public/', get_all_course_public, name='get_all_course_public'),
    
    path('course_update_by_id/', course_update_by_id, name='course_update_by_id'),
    path('get_all_course_enrolled/', get_all_course_enrolled, name='get_all_course_enrolled'),
    path('course_add/', course_add, name='course_add'),
    path('course_delete_by_id/', course_delete_by_id, name='course_delete_by_id'),
    # Topic
    path('topic_user_get_all/', topic_user_get_all, name='topic_user_get_all'),
    path('topic_admin_get_all/', topic_admin_get_all, name='topic_admin_get_all'),
    path('admin_topic_get_by_id/', admin_topic_get_by_id, name='admin_topic_get_by_id'),
    path('admin_topic_add/', admin_topic_add, name='admin_topic_add'),
    path('admin_topic_update_by_id/', admin_topic_update_by_id, name='admin_topic_update_by_id'),
    path('admin_topic_delete_by_id/', admin_topic_delete_by_id, name='admin_topic_delete_by_id'),
    #Vocabulary
    path('user_learn_vocabulary_get/', user_learn_vocabulary_get, name='user_learn_vocabulary_get'),
    path('user_learn_vocabulary_post/', user_learn_vocabulary_post, name='user_learn_vocabulary_post'),
    path('vocabulary_get_all/', UserListVocabularyViewSet.as_view(), name="vocabulary_get_all"),
    path('user_skip_vocabulary/',user_skip_vocabulary),
    path('random_vocab/',GetRandomTenWordsView.as_view(), name='random_vocab'),
    path('random_word_review/', GetRandomWordsInReviewView.as_view(), name='random_word_review'),

    path('admin_vocabulary_add/', admin_vocabulary_add, name='admin_vocabulary_add'),
    path('admin_vocabulary_update_by_id/', admin_vocabulary_update_by_id, name='admin_vocabulary_update_by_id'),
    path('admin_vocabulary_delete_by_id/', admin_vocabulary_delete_by_id, name='admin_vocabulary_delete_by_id'),

    path('set_next_review/', set_next_review, name='set_next_review'),
    path('user_vocab_process/', user_vocab_process, name='user_vocab_process'),
    path('get_all_learned_vocabulary/', get_all_learned_vocabulary, name='get_all_learned_vocabulary'),
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
    #UserEnrolled
    path('delete_student_from_course/',delete_student_from_course),
    path('enroll_student/',enroll_student),
    path('get_all_students_from_course/',get_all_students_from_course),
    path('detect_audio/',SpeechToTextAPIView.as_view(),name='detect_audio'),
    path('student_enroll_course/',student_enroll_course),
    #VocabularyNeedReview
    path('get_courses_need_review/',get_courses_need_review),
    path('get_vocabularies_need_review/',get_vocabularies_need_review),
    #leader_board
    path('leader_board/',LeaderBoardView.as_view(),name='leader_board'),
    path('get_list_student/',get_list_student),
    path('student_topics_progress_detail/',student_topics_progress_detail),
    path('student_point/',StudentPoint.as_view(),name='student_point')
    
]
