from django.urls import path
from .consumers import WordChainConsumer

websocket_urlpatterns = [
    path("ws/wordchain/", WordChainConsumer.as_asgi()),
]
