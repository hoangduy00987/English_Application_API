from django.db import models
from django.contrib.auth.models import User


class ListeningTopic(models.Model):
    name = models.CharField(max_length=100, null=True, blank=True)
    image = models.ImageField(upload_to='listening_topic_images/', null=True, blank=True)
    is_public = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class ListeningExercise(models.Model):
    listening_topic = models.ForeignKey(ListeningTopic, on_delete=models.CASCADE, related_name='listening_exercises')
    name = models.CharField(max_length=255, null=True, blank=True)
    audio_file = models.FileField(upload_to='audio_listenings/', null=True, blank=True)
    transcript = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.listening_topic.name} - {self.name}"

class UserListeningTopicProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    listening_topic = models.ForeignKey(ListeningTopic, on_delete=models.CASCADE, related_name='listening_topics')
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} - Topic: {self.listening_topic.name} - Completed: {str(self.is_completed)}"

class UserListeningExerciseResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    listening_exercise = models.ForeignKey(ListeningExercise, on_delete=models.CASCADE, related_name='listening_exercise_results')
    is_done = models.BooleanField(default=False)
    retries_count = models.PositiveSmallIntegerField(default=0)
    
    def __str__(self):
        return f"{self.user.email} - Exercise: {self.listening_exercise.name} - Done: {str(self.is_done)}"
