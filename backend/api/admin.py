from django.contrib import admin
from .submodels.models_user import *
# Register your models here.
admin.site.register(Profile)
admin.site.register(PasswordResetToken)