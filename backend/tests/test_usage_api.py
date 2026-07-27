from __future__ import annotations

from app.core.config import Settings, get_settings
from app.main import app
from app.models import GitHubInstallation, Repository
from app.services import credits
from tests.conftest import requires_db

pytestmark = requires_db


def _seed_repo(db, user_id: int) -> Repository:
    inst = GitHubInstallation(
        installation_id=7201,
        account_login="acme",
        account_type="Organization",
        owner_user_id=user_id,
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id,
        github_repo_id=99,
        full_name="acme/creditrepo",
        default_branch="main",
        private=True,
    )
    db.add(repo)
    db.flush()
    return repo


def test_usage_endpoint_reports_full_balance_initially(authed_client):
    api_client, _ = authed_client
    resp = api_client.get("/api/v1/usage")
    assert resp.status_code == 200
    body = resp.json()
    assert body["limit"] > 0
    assert body["used"] == 0
    assert body["remaining"] == body["limit"]
    assert body["resets_in_seconds"] > 0


def test_usage_endpoint_reflects_consumption(authed_client, db_session):
    api_client, user = authed_client
    settings = get_settings()
    credits.consume(
        db_session,
        user.id,
        limit=settings.user_daily_credits,
        window_seconds=settings.credit_window_seconds,
        amount=2,
    )
    body = api_client.get("/api/v1/usage").json()
    assert body["used"] == 2
    assert body["remaining"] == body["limit"] - 2


def test_ai_endpoint_blocked_with_429_when_credits_exhausted(authed_client, db_session):
    api_client, user = authed_client
    small = Settings(_env_file=None, user_daily_credits=1)
    app.dependency_overrides[get_settings] = lambda: small
    try:
        repo = _seed_repo(db_session, user.id)
        # Spend the single allotted credit, then the guard must reject.
        credits.consume(
            db_session, user.id, limit=1, window_seconds=small.credit_window_seconds
        )
        resp = api_client.post(
            f"/api/v1/repositories/{repo.id}/analyze-pr", json={"pr_number": 5}
        )
        assert resp.status_code == 429
        assert "credit" in resp.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_settings, None)
