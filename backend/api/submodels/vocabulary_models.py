from django.db import models
from django.contrib.auth.models import User
from datetime import datetime


class Topic(models.Model):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='topic_image/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(null=True,blank=True)
    updated_at = models.DateTimeField(null=True,blank=True)
    level = models.CharField(max_length=255)

class Vocabulary(models.Model):
    topic_id = models.ForeignKey(Topic, models.CASCADE)
    word = models.CharField(max_length=255)
    transcription = models.CharField(max_length=255)
    meaning = models.CharField(max_length=255)
    example = models.TextField(blank=True, null=True)
    pronunciation = models.ImageField(upload_to='audio/', blank=True, null=True)
    created_at = models.DateTimeField(null=True,blank=True)
    updated_at = models.DateTimeField(null=True,blank=True)