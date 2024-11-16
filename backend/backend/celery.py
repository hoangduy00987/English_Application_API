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
        'schedule': timedelta(days=1),
    },
    'send-reminder-email-every-day': {
        'task': 'api.login.tasks.send_reminder_email',
        'schedule': timedelta(minutes=5),
    },
    'check-expo-tokens-weekly': {
        'task': 'api.login.tasks.periodic_token_check',
        'schedule': crontab(day_of_week=1, hour=0, minute=0),
    },'reset-weekly-points': {
        'task': 'api.vocabulary.tasks.reset_week_leaderboard_points',  
        'schedule': crontab(minute=59, hour=23, day_of_week=6), 
    },'reset-monthly-points': {
        'task': 'api.vocabulary.tasks.reset_month_leaderboard_points',  
        'schedule': crontab(minute=59, hour=23, day=28), 
    },
}
