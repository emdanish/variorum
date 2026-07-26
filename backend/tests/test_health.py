from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app"] == "Variorum"
    assert isinstance(body["ai_available"], bool)
    assert isinstance(body["ai_providers"], list)


def test_install_url_endpoint():
    response = client.get("/api/v1/github/install-url")
    assert response.status_code == 200
    assert response.json()["install_url"].startswith("https://github.com/apps/")


def test_webhook_rejects_unsigned_request():
    response = client.post("/webhooks/github", content=b"{}")
    assert response.status_code == 401
