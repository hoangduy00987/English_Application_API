from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from ..submodels.models_vocabulary import UserVocabularyProcess,LeaderBoard
import calendar

@shared_task
def update_review_status():
   
    now = timezone.now()
    processes = UserVocabularyProcess.objects.filter(
        is_learned=True, last_learned_at__lt=now - timedelta(hours=1)
    )
    
    for process in processes:
        process.is_need_review = True
        process.save()
    return f"{processes.count()} vocabulary processes updated for review."

@shared_task
def reset_week_leaderboard_points():
    now = timezone.now()
    week = now.isocalendar()[1]
    leaderboard_week = LeaderBoard.objects.filter(year_week=week)
    for entry in leaderboard_week:
        entry.weekly_points = 0
        entry.save()

@shared_task
def reset_month_leaderboard_points():
        now = timezone.now()
        month = now.month
        year = now.year
        last_day_of_month = calendar.monthrange(year, month)[1]  
        if now.day == last_day_of_month:
            leaderboard_month = LeaderBoard.objects.filter(year_month=month)
            for entry in leaderboard_month:
                entry.monthly_points = 0
                entry.save()