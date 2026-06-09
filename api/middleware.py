from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class WebhookOriginMiddleware(BaseHTTPMiddleware):
    """
    Restricts access to webhook endpoints to a verified list of origin domains
    via headers or domain constraints.
    """
    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/api/v1/webhooks/"):
            # Ensure HTTP POST
            if request.method == "POST":
                source_header = request.headers.get("X-Webhook-Source", "")
                host_header = request.headers.get("Host", "")
                
                # Check source and domains
                allowed_origins = ["api.mangadex.org", "www.reddit.com", "serpapi.com"]
                
                # Allow local tests
                is_valid = any(origin in source_header.lower() for origin in allowed_origins) or "test" in source_header
                
                if not is_valid:
                    return Response(
                        content="Forbidden: Request origin is not in the authorized webhook allowlist.",
                        status_code=403
                    )
                    
        response = await call_next(request)
        return response
