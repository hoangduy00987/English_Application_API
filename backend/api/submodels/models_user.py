from django.db import models
from django.contrib.auth.models import User
from datetime import datetime


class Profile(models.Model):
    user = models.OneToOneField(User, related_name='user', on_delete=models.CASCADE)
    is_first_login = models.BooleanField(default=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    full_name = models.CharField(max_length=255)
    gender = models.BooleanField(default=False)
    english_level = models.CharField(max_length=100,null=True,blank=True)
    daily_study_time = models.CharField(max_length=100,null=True,blank=True)
    phone_number = models.CharField(max_length=20,null=True,blank=True)
    avatar = models.ImageField(upload_to='avatar/', blank=True, null=True)
    expo_push_token = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    def __str__(self):
        return str(self.user)

class PasswordResetToken(models.Model):
    uid = models.CharField(max_length=255)
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.uid} - {self.token}'
    
