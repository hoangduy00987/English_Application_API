from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from ..submodels.models_user import UserActivity
from .notifications import push_notification, send_notification_email, check_and_update_tokens
import asyncio

@shared_task
def check_and_send_notification():
    duration = timezone.now() - timedelta(minutes=10)
    inactive_users = UserActivity.objects.filter(last_activity__lt=duration)

    for user_activity in inactive_users:
        if user_activity.expo_push_token:
            push_notification(
                to=user_activity.expo_push_token,
                title='Hello bạn',
                body='Vào mà học tiếng Anh đi đừng có mà lười! Định trốn đến khi nào?'
            )
        print('start')
        send_notification_email(
            subject='Nhắc nhở việc học tiếng Anh',
            message='Vào mà học tiếng Anh đi đừng có mà lười! Định trốn đến khi nào?',
            to=user_activity.user.email
        )
        print('end')

@shared_task
def periodic_token_check():
    # Get all tokens from database
    tokens = UserActivity.objects.exclude(expo_push_token__isnull=True).values_list('expo_push_token', flat=True)
    # Run async function in sync environment of Celery
    asyncio.run(check_and_update_tokens(list(tokens)))
