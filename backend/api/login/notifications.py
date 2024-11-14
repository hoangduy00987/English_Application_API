from exponent_server_sdk import PushClient, PushMessage
from ..submodels.models_user import Profile
import asyncio
import logging

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

# Async function to check and update expired expo push token
async def check_and_update_tokens(tokens):
    try:
        response = await client.get_push_notification_receipts(tokens)
        for token, receipt in response.items():
            if receipt['status'] == 'error':
                Profile.objects.filter(expo_push_token=token).update(expo_push_token=None)
    except Exception as error:
        logger.error(f'Error checking push receipts: {str(error)}')
