import json
import jwt
from django.conf import settings
from channels.generic.websocket import AsyncJsonWebsocketConsumer

class FeedConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.room_group_name = f"feed_{self.user_id}"

        # JWT validation (optional for MVP dev env, but implemented for security)
        # Try to extract JWT from headers or query string
        authorized = True
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        token = None
        
        # Look in query string ?token=...
        if 'token=' in query_string:
            token = query_string.split('token=')[-1].split('&')[0]
            
        if token:
            try:
                jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            except jwt.ExpiredSignatureError:
                authorized = False
            except jwt.InvalidTokenError:
                authorized = False

        if not authorized:
            await self.close(code=4003)
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def feed_update(self, event):
        await self.send_json({
            'type': 'feed.update',
            'webtoons': event.get('webtoons', [])
        })

    async def scrape_status(self, event):
        await self.send_json({
            'type': 'scrape.status',
            'message': event.get('message', '')
        })

    async def preference_updated(self, event):
        await self.send_json({
            'type': 'preference.updated',
            'preferences': event.get('preferences', {})
        })

    async def error(self, event):
        await self.send_json({
            'type': 'error',
            'message': event.get('message', '')
        })
