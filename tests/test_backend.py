import os
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.config import settings
from backend.database import init_db, engine
from sqlalchemy import text

client = TestClient(app)

def test_config_loading():
    assert settings.app_name == "Email Sender Pro"
    assert settings.database_url is not None
    assert isinstance(settings.cors_origins, list)
    assert len(settings.cors_origins) > 0

def test_database_initialization():
    # Ensure database tables can be created without error
    init_db()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "Email Sender Pro"
    assert data["database"] == "connected"
    assert "environment" in data

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Welcome" in data["message"]

def test_cors_headers():
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET"
        }
    )
    # TestClient or CORS middleware handling
    assert response.status_code in [200, 204]
    cors_header = response.headers.get("access-control-allow-origin")
    if cors_header:
        assert cors_header in settings.cors_origins or cors_header == "*"

def test_drafts_api():
    # Test GET drafts initially
    response = client.get("/api/drafts")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    # Test POST draft
    draft_data = {
        "from_name": "Test Sender",
        "subject": "Hello Draft",
        "recipient": "user@example.com",
        "body": "Test draft body",
        "attachments": "[]"
    }
    create_res = client.post("/api/drafts", json=draft_data)
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["subject"] == "Hello Draft"
    assert created["from_name"] == "Test Sender"
    draft_id = created["id"]

    # Test PUT update draft
    update_res = client.put(f"/api/drafts/{draft_id}", json={"subject": "Updated Subject"})
    assert update_res.status_code == 200
    assert update_res.json()["subject"] == "Updated Subject"

    # Test DELETE draft
    del_res = client.delete(f"/api/drafts/{draft_id}")
    assert del_res.status_code == 204

