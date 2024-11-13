from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from django.conf import settings

@shared_task
def send_reminder_email():
    three_days_ago = timezone.now() - timedelta(seconds=30)
    inactive_users = User.objects.filter(last_login__lt=three_days_ago)

    for user in inactive_users:
        # Gửi email thông báo cho người dùng
        send_mail(
            'We Miss You!',
            'It has been 3 days since your last login. Come back and continue your learning!',
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
    return f"Sent reminder emails to {inactive_users.count()} users."
