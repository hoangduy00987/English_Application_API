from exponent_server_sdk import PushClient, PushMessage
from django.core.mail import send_mail
from django.conf import settings
from ..submodels.models_user import UserActivity
import asyncio
import logging
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)
client = PushClient()

# Push notification for mobile app
def push_notification(to, title, body, data=None):
    try:
        response = client.publish(
            PushMessage(
                to=to,
                title=title,
                body=body,
                data=data
            )
        )
    except Exception as error:
        print(f'Error sending push notification: {error}')
        logger.error(f'Error sending push notification: {str(error)}')
    else:
        print(f'Push notification sent successfully: {response}')


# Send email for web users
def send_notification_email(subject, message, to):
    try:
        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = settings.EMAIL_HOST_USER
        msg['To'] = [to]
        msg.set_content(message)

        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            server.starttls()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.send_message(msg)
        
        print("Email sent successfully")
        # send_mail(
        #     subject=subject,
        #     message=message,
        #     from_email=settings.EMAIL_HOST_USER,
        #     recipient_list=[to],
        #     fail_silently=False
        # )
    except Exception as error:
        print(f'Error sending notification email: {error}')
        logger.error(f'Error sending notification email: {str(error)}')


# Async function to check and update expired expo push token
async def check_and_update_tokens(tokens):
    try:
        response = await client.get_push_notification_receipts(tokens)
        for token, receipt in response.items():
            if receipt['status'] == 'error':
                UserActivity.objects.filter(expo_push_token=token).update(expo_push_token=None)
    except Exception as error:
        logger.error(f'Error checking push receipts: {str(error)}')
