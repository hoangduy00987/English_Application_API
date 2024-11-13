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
        'schedule': timedelta(seconds=30)  
    },
}