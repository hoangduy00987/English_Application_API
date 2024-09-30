from django.db import models
from django.contrib.auth.models import User
from datetime import datetime


class Topic(models.Model):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='topic_image/', blank=True, null=True)
    is_locked = models.BooleanField(default=True)
    is_public = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(null=True,blank=True)
    updated_at = models.DateTimeField(null=True,blank=True)
    order = models.IntegerField(null=True, blank=False, unique=True)
    times_studied = models.IntegerField(null=True)
    def __str__(self) -> str:
        return self.name
    
class Vocabulary(models.Model):
    topic_id = models.ForeignKey(Topic, related_name='vocabularies',on_delete=models.CASCADE)
    word = models.CharField(max_length=255)
    transcription = models.CharField(max_length=255)
    meaning = models.CharField(max_length=255)
    example = models.TextField(blank=True, null=True)
    pronunciation = models.ImageField(upload_to='audio_pronun_file/', blank=True, null=True)
    created_at = models.DateTimeField(null=True,blank=True)
    updated_at = models.DateTimeField(null=True,blank=True)
    is_deleted = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=1,unique=True)

    def __str__(self) -> str:
        return self.word
    

class UserVocabularyProcess(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    vocabulary_id = models.ForeignKey(Vocabulary,  on_delete=models.CASCADE)
    learned_at = models.DateTimeField(null=True)
    review_count = models.IntegerField(null=True)
    next_review_at  =  models.DateTimeField(null=True)
    completed_words = models.IntegerField(null=True)
    is_learned = models.BooleanField(null=True)

    def __str__(self) -> str:
        return self.vocabulary_id.word
