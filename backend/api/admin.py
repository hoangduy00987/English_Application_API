from django.contrib import admin
from .submodels.models_user import *
from .submodels.models_vocabulary import *
from .submodels.models_activity import *
from .submodels.models_listening import *

# Register your models here.
admin.site.register(Profile)
admin.site.register(PasswordResetToken)
admin.site.register(Topic)
admin.site.register(Vocabulary)
admin.site.register(UserVocabularyProcess)
admin.site.register(MiniExercise)
admin.site.register(MiniExerciseFillinAnswer)
admin.site.register(MiniExerciseMultipleChoicesAnswer)
admin.site.register(UserTopicProgress)
admin.site.register(Course)
admin.site.register(UserCourseEnrollment)
admin.site.register(Streak)
admin.site.register(LearningActivity)
admin.site.register(ListeningTopic)
admin.site.register(ListeningExercise)
admin.site.register(UserListeningTopicProgress)
admin.site.register(UserListeningExerciseResult)
