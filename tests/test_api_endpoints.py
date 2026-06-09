import os
import django
from fastapi.testclient import TestClient

# Setup Django configuration for API tests
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spellscroll.settings')
django.setup()

from api.main import app

client = TestClient(app)

def test_api_health_check():
    # Verify health status route returns 200
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "FastAPI" in data["service"]

def test_anonymous_unauthorized():
    # Verify that requesting feed without authorization returns 401
    response = client.get("/api/v1/feed/current")
    assert response.status_code == 401
