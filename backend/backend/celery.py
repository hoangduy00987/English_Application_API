import os
from celery import Celery
from datetime import timedelta
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

app = Celery('backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
app.conf.beat_schedule = {
    'update-review-status-every-day': {
        'task': 'api.vocabulary.tasks.update_review_status',
        'schedule': timedelta(days=1),  # Chạy mỗi ngày
    },
    'send-reminder-email-every-day': {
        'task': 'api.login.tasks.send_reminder_email',
        'schedule': timedelta(hours=1),  # Chạy mỗi giờ
    },
    'check-expo-tokens-weekly': {
        'task': 'api.login.tasks.periodic_token_check',
        'schedule': crontab(day_of_week=1, hour=0, minute=0),  # Chạy mỗi tuần vào thứ 2 lúc 00:00
    },
    'reset-weekly-points': {
        'task': 'api.vocabulary.tasks.reset_week_leaderboard_points',  
        'schedule': crontab(minute=59, hour=23, day_of_week=6),  # Chạy mỗi tuần vào lúc 11:59 PM thứ 7
    },
    'reset-monthly-points': {
        'task': 'api.vocabulary.tasks.reset_month_leaderboard_points',  
        'schedule': crontab(minute=59, hour=23, day_of_month=28),  # Chạy vào ngày 28 mỗi tháng lúc 11:59 PM
    },
}