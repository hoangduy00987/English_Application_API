from django.db import models
from django.contrib.auth.models import User


class Streak(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_streak')
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_streak_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.email} - Current Streak: {self.current_streak}"

class LearningActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='learning_activities')
    activity_date = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'activity_date')
        ordering = ['-activity_date']
    
    def __str__(self):
        return f"{self.user.email} - {self.activity_date} - Completed: {self.is_completed}"
