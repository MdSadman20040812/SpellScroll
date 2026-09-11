"""Per-user feed WebSocket.

Authorisation note: the previous implementation defaulted ``authorized`` to
True and only rejected a token that was present *and* invalid.  Connecting with
no token at all therefore succeeded, so any client could join
``feed_<uuid>`` and receive another account's recommendations.  Identity is now
established from the session (or the auth cookie) and must match the room.
"""
import logging

import jwt
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.conf import settings

logger = logging.getLogger(__name__)

CLOSE_UNAUTHORISED = 4003


class FeedConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope["url_route"]["kwargs"]["user_id"]
        self.room_group_name = "feed_{0}".format(self.user_id)

        identity = self._identify()
        if identity is None or identity != self.user_id:
            await self.close(code=CLOSE_UNAUTHORISED)
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    def _identify(self):
        """Return the authenticated user id for this connection, or None."""
        user = self.scope.get("user")
        if user is not None and getattr(user, "is_authenticated", False):
            return str(user.id)

        # Fall back to the httpOnly access_token cookie that the login view
        # sets, which is what non-session clients (the Next.js app) present.
        token = self._cookie("access_token")
        if not token:
            return None
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        except jwt.PyJWTError:
            return None
        return payload.get("user_id")

    def _cookie(self, name):
        cookies = self.scope.get("cookies") or {}
        if cookies:
            return cookies.get(name)
        for header, value in self.scope.get("headers") or []:
            if header == b"cookie":
                for part in value.decode("latin-1").split(";"):
                    key, _, val = part.strip().partition("=")
                    if key == name:
                        return val
        return None

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(
                self.room_group_name, self.channel_name
            )

    async def feed_update(self, event):
        await self.send_json({"type": "feed.update", "webtoons": event.get("webtoons", [])})

    async def scrape_status(self, event):
        await self.send_json({"type": "scrape.status", "message": event.get("message", "")})

    async def preference_updated(self, event):
        await self.send_json(
            {"type": "preference.updated", "preferences": event.get("preferences", {})}
        )

    async def error(self, event):
        await self.send_json({"type": "error", "message": event.get("message", "")})
