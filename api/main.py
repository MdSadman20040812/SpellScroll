import os
import django
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI application
app = FastAPI(
    title="SpellScroll REST Backend",
    version="1.0.0",
    docs_url="/api/v1/docs",
    openapi_url="/api/v1/openapi.json"
)

# CORS Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root-level health endpoint
@app.get("/api/v1/health")
def health_check():
    return {"status": "healthy", "service": "SpellScroll FastAPI In-Process Backend"}

# Import routers after app registration to avoid circular imports during setup
from api.routers import onboarding, feed, webtoons, admin

app.include_router(onboarding.router, prefix="/api/v1/onboarding", tags=["Onboarding"])
app.include_router(feed.router, prefix="/api/v1/feed", tags=["Feed"])
app.include_router(webtoons.router, prefix="/api/v1/webtoons", tags=["Webtoons"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
