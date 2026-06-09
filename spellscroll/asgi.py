import os
import django
from django.core.asgi import get_wsgi_application

# Set settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spellscroll.settings')
django.setup()

from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()

# Now import ASGI/FastAPI components safely after django setup
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path

# We will define the consumer in apps.feed.routing/consumers
import apps.feed.routing

# We import the FastAPI app here (api/main.py)
from api.main import app as fastapi_app

class UnifiedASGIApp:
    """
    Dispatches HTTP requests starting with /api/v1/ directly to FastAPI.
    All other HTTP/WebSocket requests go to Django / Django Channels.
    """
    def __init__(self, django_app, fastapi_app):
        self.django_app = django_app
        self.fastapi_app = fastapi_app

    async def __call__(self, scope, receive, send):
        path_str = scope.get('path', '')
        if scope['type'] == 'http' and path_str.startswith('/api/v1/'):
            # Route directly to FastAPI
            await self.fastapi_app(scope, receive, send)
        elif scope['type'] == 'websocket' and path_str.startswith('/api/v1/ws/'):
            # Route /api/v1/ws/ to FastAPI WebSocket handlers (optional)
            await self.fastapi_app(scope, receive, send)
        else:
            # Route to Django Channels (which handles WS and standard HTTP)
            await self.django_app(scope, receive, send)

channels_router = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            apps.feed.routing.websocket_urlpatterns
        )
    ),
})

application = UnifiedASGIApp(django_app=channels_router, fastapi_app=fastapi_app)
