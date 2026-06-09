from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'^ws/feed/(?P<user_id>[^/]+)/$', consumers.FeedConsumer.as_asgi()),
]
