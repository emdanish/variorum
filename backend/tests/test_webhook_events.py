from __future__ import annotations

from sqlalchemy import select

from app.models import GitHubInstallation, Repository
from app.services.github.events import dispatch_webhook
from tests.conftest import requires_db

pytestmark = requires_db


def _installation_created(installation_id: int = 10) -> dict:
    return {
        "action": "created",
        "installation": {
            "id": installation_id,
            "account": {"login": "acme", "type": "Organization"},
        },
        "repositories": [
            {"id": 1, "full_name": "acme/api", "private": True},
            {"id": 2, "full_name": "acme/web", "private": False},
        ],
    }


def _count_installations(db) -> int:
    return len(db.execute(select(GitHubInstallation)).scalars().all())


def test_installation_created_persists_installation_and_repos(db_session):
    result = dispatch_webhook(db_session, "installation", _installation_created())
    assert result == "installation:created"
    inst = db_session.execute(select(GitHubInstallation)).scalar_one()
    assert inst.account_login == "acme"
    repos = db_session.execute(select(Repository)).scalars().all()
    assert {r.full_name for r in repos} == {"acme/api", "acme/web"}


def test_installation_deleted_removes_installation_and_repos(db_session):
    dispatch_webhook(db_session, "installation", _installation_created(11))
    result = dispatch_webhook(
        db_session,
        "installation",
        {"action": "deleted", "installation": {"id": 11}},
    )
    assert result == "installation:deleted"
    assert _count_installations(db_session) == 0
    assert db_session.execute(select(Repository)).scalars().all() == []


def test_installation_suspend_sets_suspended(db_session):
    dispatch_webhook(db_session, "installation", _installation_created(12))
    dispatch_webhook(
        db_session,
        "installation",
        {
            "action": "suspend",
            "installation": {"id": 12, "account": {"login": "acme", "type": "Organization"}},
        },
    )
    inst = db_session.execute(
        select(GitHubInstallation).where(GitHubInstallation.installation_id == 12)
    ).scalar_one()
    assert inst.suspended_at is not None


def test_installation_repositories_added_and_removed(db_session):
    dispatch_webhook(db_session, "installation", _installation_created(13))
    added = dispatch_webhook(
        db_session,
        "installation_repositories",
        {
            "installation": {"id": 13, "account": {"login": "acme", "type": "Organization"}},
            "repositories_added": [{"id": 3, "full_name": "acme/docs", "private": True}],
            "repositories_removed": [{"id": 1, "full_name": "acme/api", "private": True}],
        },
    )
    assert added == "installation_repositories:+1/-1"
    names = {
        r.full_name for r in db_session.execute(select(Repository)).scalars().all()
    }
    assert names == {"acme/web", "acme/docs"}


def test_unknown_event_ignored(db_session):
    assert dispatch_webhook(db_session, "star", {}) == "ignored:star"


def test_pull_request_acknowledged(db_session):
    assert dispatch_webhook(db_session, "pull_request", {"action": "opened"}) == (
        "acknowledged:pull_request"
    )
