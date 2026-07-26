from __future__ import annotations

from app.models import ApiToken, User
from app.services import tokens as svc
from tests.conftest import requires_db

pytestmark = requires_db


def test_generate_format():
    token, prefix, token_hash = svc.generate()
    assert token.startswith("vrm_")
    assert prefix == token[:12]
    assert len(token_hash) == 64  # sha-256 hex
    assert token_hash != token  # stored hash is not the plaintext


def test_create_stores_hash_not_plaintext(db_session):
    u = User(email="tok@example.com", github_user_id=8800)
    db_session.add(u)
    db_session.flush()
    row, plaintext = svc.create_token(db_session, u.id, "ci")
    assert plaintext.startswith("vrm_")
    assert row.token_hash != plaintext
    assert row.prefix == plaintext[:12]
    # plaintext is not persisted anywhere
    stored = db_session.get(ApiToken, row.id)
    assert stored.token_hash == svc._hash(plaintext)


def test_resolve_and_revoke(db_session):
    u = User(email="tok2@example.com", github_user_id=8801)
    db_session.add(u)
    db_session.flush()
    row, plaintext = svc.create_token(db_session, u.id, "ci")

    resolved = svc.resolve_token(db_session, plaintext)
    assert resolved is not None and resolved.id == u.id
    assert svc.resolve_token(db_session, "vrm_wrong") is None
    assert svc.resolve_token(db_session, "not-a-token") is None

    assert svc.revoke_token(db_session, u.id, row.id) is True
    assert svc.resolve_token(db_session, plaintext) is None
    assert svc.revoke_token(db_session, u.id, row.id) is False  # already gone


def test_token_endpoints(authed_client, db_session):
    api_client, user = authed_client
    created = api_client.post("/api/v1/auth/tokens", json={"name": "CI"})
    assert created.status_code == 200
    data = created.json()
    assert data["token"].startswith("vrm_")
    assert data["name"] == "CI"

    listed = api_client.get("/api/v1/auth/tokens")
    assert listed.status_code == 200
    rows = listed.json()
    assert len(rows) == 1
    assert "token" not in rows[0]  # plaintext never listed

    assert api_client.delete(f"/api/v1/auth/tokens/{data['id']}").status_code == 204
    assert api_client.get("/api/v1/auth/tokens").json() == []


def test_bearer_auth_grants_access(client, db_session):
    # No session; authenticate purely via a personal API token.
    u = User(email="bearer@example.com", name="Bearer", github_user_id=8802)
    db_session.add(u)
    db_session.flush()
    _, plaintext = svc.create_token(db_session, u.id, "ci")

    ok = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {plaintext}"})
    assert ok.status_code == 200
    assert ok.json()["email"] == "bearer@example.com"

    bad = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer vrm_bad"})
    assert bad.status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 401


def test_token_endpoints_require_auth(client):
    assert client.get("/api/v1/auth/tokens").status_code == 401
    assert client.post("/api/v1/auth/tokens", json={"name": "x"}).status_code == 401
