from rest_framework import serializers
from ..submodels.models_activity import Streak, LearningActivity
from datetime import date, timedelta
from django.utils import timezone


class UserStreakSerializer(serializers.ModelSerializer):
    current_streak = serializers.SerializerMethodField()

    class Meta:
        model = Streak
        fields = ['id', 'current_streak', 'longest_streak', 'last_streak_date']
    
    def get_current_streak(self, obj):
        if obj.last_streak_date:
            today = date.today()
            if obj.last_streak_date < today - timedelta(days=1):
                return 0
            return obj.current_streak
        return 0

class LearningActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningActivity
        fields = ['id', 'activity_date', 'is_completed']
    
    def save(self, request):
        try:
            user = request.user
            today = timezone.now().date()

            if LearningActivity.objects.filter(user=user, activity_date=today, is_completed=True).exists():
                return None

            activity, created = LearningActivity.objects.get_or_create(
                user=user,
                activity_date=today,
                defaults={"is_completed": True}
            )
            if not created:
                activity.is_completed = True
                activity.save()
            
            streak = Streak.objects.get(user=user)
            last_date = streak.last_streak_date if streak.last_streak_date else today
            
            # Update streak
            if last_date == today - timedelta(days=1):
                streak.current_streak += 1
            else:
                streak.current_streak = 1
            
            streak.last_streak_date = today

            # Update longest streak
            if streak.current_streak > streak.longest_streak:
                streak.longest_streak = streak.current_streak
            
            streak.save()
            
            return activity
        except Exception as error:
            print("update learning activity error:", error)
            return None
