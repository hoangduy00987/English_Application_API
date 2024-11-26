from django.db import models
from django.contrib.auth.models import User
from datetime import datetime
from django.utils import timezone


class Course(models.Model):
    name = models.CharField(max_length=255,null=True)
    description = models.TextField(null=True)
    image = models.ImageField(upload_to='course_imgae/',null=True)
    is_public = models.BooleanField(null=True)
    is_deleted = models.BooleanField(null=True)
    update_at = models.DateTimeField(null=True)
    def __str__(self) -> str:
        return self.name

class UserCourseEnrollment(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    course_id = models.ForeignKey(Course, on_delete=models.CASCADE,null=True)
    enrolled_at = models.DateTimeField(null=True)
    def __str__(self) -> str:
        return f"{self.user_id} - {self.course_id.name}"

class Topic(models.Model):
    course_id = models.ForeignKey(Course,on_delete=models.CASCADE,null=True)
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='topic_image/', blank=True, null=True)
    is_public = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    def __str__(self) -> str:
        return self.name


class UserTopicProgress(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    topic_id = models.ForeignKey(Topic, related_name='topic',on_delete=models.CASCADE,null=True)
    is_locked = models.BooleanField(default=True)
    is_completed = models.BooleanField(default=False)


    def __str__(self) -> str:
        return  self.topic_id.name
    
class Vocabulary(models.Model):
    topic_id = models.ForeignKey(Topic, related_name='vocabularies',on_delete=models.CASCADE)
    word = models.CharField(max_length=255)
    transcription = models.CharField(max_length=255)
    meaning = models.CharField(max_length=255)
    example = models.TextField(blank=True, null=True)
    word_image = models.ImageField(upload_to='word_images/', blank=True, null=True)
    pronunciation_audio = models.FileField(upload_to='audio_pronun_files/', blank=True, null=True)
    pronunciation_video = models.FileField(upload_to='video_pronun_files/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.word
    

class UserVocabularyProcess(models.Model):
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)
    vocabulary_id = models.ForeignKey(Vocabulary, related_name="vocab_processes", on_delete=models.CASCADE)
    review_count = models.IntegerField(null=True)
    next_review_at  =  models.DateTimeField(null=True)
    is_learned = models.BooleanField(null=True)
    last_learned_at = models.DateTimeField(null=True)
    is_need_review = models.BooleanField(default=False)
    is_skipped = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.vocabulary_id.word
    def update_review_status(self):
        if (timezone.now() - self.learned_at).total_seconds() >= 60:
            self.is_need_review = True
            self.save()
    
# Exercise type choices
EXERCISE_TYPE = [
    ('T1', 'Fill in exercise'),
    ('T2', 'Multiple choices exercise')
]

class MiniExercise(models.Model):
    vocabulary_id = models.ForeignKey(Vocabulary, on_delete=models.CASCADE)
    exercise_type = models.CharField(max_length=50, choices=EXERCISE_TYPE)
    content = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.vocabulary_id.word + ': ' + self.content + '-' + self.exercise_type
    
class MiniExerciseFillinAnswer(models.Model):
    exercise_id = models.ForeignKey(MiniExercise, on_delete=models.CASCADE)
    correct_answer = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.exercise_id.vocabulary_id.word + ': ' + self.exercise_id.content + ' Answer-' + self.correct_answer
    
class MiniExerciseMultipleChoicesAnswer(models.Model):
    exercise_id = models.ForeignKey(MiniExercise, on_delete=models.CASCADE)
    answer = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.exercise_id.vocabulary_id.word + ': ' + self.exercise_id.content + '-' + self.answer + ': ' + str(self.is_correct)

class LeaderBoard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,null=True,blank=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, null=True, blank=True)
    total_points = models.IntegerField(default=0)
    weekly_points = models.IntegerField(default=0)
    monthly_points = models.IntegerField(default=0)
    year_week = models.IntegerField(default=1)
    year_month = models.IntegerField(default=1)
    update_at = models.DateTimeField(null=True)

    def __str__(self):
        return f"Leaderboard: {self.user.username}  - {self.total_points} points"
    #