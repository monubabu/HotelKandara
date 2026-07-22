from django.urls import re_path
from .consumers import AvailabilityConsumer

websocket_urlpatterns = [
    re_path(r'ws/availability/$', AvailabilityConsumer.as_asgi()),
]