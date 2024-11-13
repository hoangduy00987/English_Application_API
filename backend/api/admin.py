from django.contrib import admin
from .submodels.models_user import *
from .submodels.models_vocabulary import *
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