"""Async bridge helpers for calling synchronous Django ORM / blocking code from FastAPI."""
from asgiref.sync import sync_to_async

def sync_call(func, *args, **kwargs):
    """Run a synchronous function in a thread and return its result."""
    return sync_to_async(func)(*args, **kwargs)

class SyncQuerySet:
    """Wrap a Django QuerySet so its methods can be awaited."""
    def __init__(self, qs):
        self._qs = qs

    def __getattr__(self, name):
        attr = getattr(self._qs, name)
        if callable(attr):
            async def _wrapper(*args, **kwargs):
                return await sync_to_async(attr)(*args, **kwargs)
            return _wrapper
        return attr
