from __future__ import annotations

from app.core.config import Settings, get_settings
from app.main import app
from app.models import GitHubInstallation, Repository
from app.services import credits
from tests.conftest import requires_db

pytestmark = requires_db


def _seed_repo(db, user_id: int) -> Repository:
    inst = GitHubInstallation(
        installation_id=7301,
        account_login="acme",
        account_type="Organization",
        owner_user_id=user_id,
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id,
        github_repo_id=123,
        full_name="acme/adminrepo",
        default_branch="main",
        private=True,
    )
    db.add(repo)
    db.flush()
    return repo


def test_admin_usage_hidden_from_non_admins(authed_client):
    # No ADMIN_GITHUB_LOGINS configured → the tester is not an admin → 404.
    api_client, _ = authed_client
    assert api_client.get("/api/v1/admin/usage").status_code == 404


def test_me_reports_admin_flag(authed_client, db_session):
    api_client, user = authed_client
    user.github_login = "bossuser"
    db_session.flush()
    admin_settings = Settings(_env_file=None, admin_github_logins="bossuser")
    app.dependency_overrides[get_settings] = lambda: admin_settings
    try:
        body = api_client.get("/api/v1/auth/me").json()
        assert body["is_admin"] is True
        assert body["github_login"] == "bossuser"
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_admin_usage_reports_fleet_stats(authed_client, db_session):
    api_client, user = authed_client
    user.github_login = "bossuser"
    db_session.flush()
    _seed_repo(db_session, user.id)

    admin_settings = Settings(
        _env_file=None, admin_github_logins="BossUser", global_daily_credits=1000
    )
    app.dependency_overrides[get_settings] = lambda: admin_settings
    try:
        # Record some fleet + per-user spend.
        credits.consume_global(
            db_session, limit=1000, window_seconds=admin_settings.credit_window_seconds, amount=7
        )
        credits.consume(
            db_session,
            user.id,
            limit=admin_settings.user_daily_credits,
            window_seconds=admin_settings.credit_window_seconds,
            amount=4,
        )
        body = api_client.get("/api/v1/admin/usage").json()
        assert body["global_used"] == 7
        assert body["global_limit"] == 1000
        assert body["global_remaining"] == 993
        assert body["total_repositories"] == 1
        assert body["total_users"] >= 1
        assert body["resets_in_seconds"] > 0
        top = {u["user_id"]: u for u in body["top_users"]}
        assert top[user.id]["used"] == 4
        assert top[user.id]["login"] == "bossuser"
    finally:
        app.dependency_overrides.pop(get_settings, None)
