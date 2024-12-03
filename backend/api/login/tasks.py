from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from ..submodels.models_user import Profile
from django.conf import settings
from .notifications import push_notification, check_and_update_tokens
import asyncio

@shared_task
def send_reminder_email():
    three_days_ago = timezone.localtime(timezone.now()) - timedelta(hours=1)
    inactive_users = Profile.objects.filter(last_activity__lt=three_days_ago)

    for user in inactive_users:
        # Gửi email thông báo cho người dùng
        send_mail(
            'We Miss You!',
            'It has been 3 days since your last login. Come back and continue your learning!',
            settings.EMAIL_HOST_USER,
            [user.user.email],
            fail_silently=False,
        )

        if user.expo_push_token:
            push_notification(
                to=user.expo_push_token,
                title='We Miss You!',
                body='It has been 3 days since your last login. Come back and continue your learning!'
            )
    return f"Sent reminder emails to {inactive_users.count()} users."

@shared_task
def periodic_token_check():
    # Get all tokens from database
    tokens = Profile.objects.exclude(expo_push_token__isnull=True).values_list('expo_push_token', flat=True)
    # Run async function in sync environment of Celery
    asyncio.run(check_and_update_tokens(list(tokens)))
