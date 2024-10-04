# chat/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/llm/(?P<llm>[\w-]+)/$', consumers.ChatConsumer.as_asgi()),
]
