from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models import GitHubInstallation, Repository, User
from app.services import schedule as svc
from tests.conftest import requires_db

pytestmark = requires_db

# A fixed Monday 09:00 UTC (2026-03-02 is a Monday → weekday() == 0).
_MON_9 = datetime(2026, 3, 2, 9, 0, tzinfo=UTC)


def _repo(db, *, seq: int, with_webhook: bool) -> Repository:
    u = User(
        email=f"sch{seq}@example.com", github_user_id=9800 + seq,
        slack_webhook_url="https://hooks.slack.com/services/T/B/x" if with_webhook else None,
    )
    db.add(u)
    db.flush()
    inst = GitHubInstallation(
        installation_id=9800 + seq, account_login="acme", account_type="User", owner_user_id=u.id
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=9801 + seq, full_name=f"acme/s{seq}",
        default_branch="main",
    )
    db.add(repo)
    db.flush()
    return repo


# --------------------------------------------------------------------------- #
# Service: CRUD + due logic
# --------------------------------------------------------------------------- #


def test_set_get_delete_schedule(db_session):
    repo = _repo(db_session, seq=0, with_webhook=True)
    assert svc.get_schedule(db_session, repo.id) is None
    row = svc.set_schedule(db_session, repo.id, day_of_week=2, hour=14, enabled=True)
    assert row.day_of_week == 2 and row.hour == 14 and row.enabled
    # upsert (not duplicate)
    row2 = svc.set_schedule(db_session, repo.id, day_of_week=3, hour=8, enabled=False)
    assert row2.id == row.id and row2.day_of_week == 3 and not row2.enabled
    assert svc.delete_schedule(db_session, repo.id) is True
    assert svc.get_schedule(db_session, repo.id) is None


def test_due_matches_weekday_hour_and_enabled(db_session):
    repo = _repo(db_session, seq=1, with_webhook=True)
    svc.set_schedule(db_session, repo.id, day_of_week=0, hour=9, enabled=True)
    due = svc.due_schedules(db_session, _MON_9)
    assert [d.repository_id for d in due] == [repo.id]
    # wrong hour → not due
    assert svc.due_schedules(db_session, _MON_9.replace(hour=10)) == []
    # wrong day → not due
    assert svc.due_schedules(db_session, _MON_9 + timedelta(days=1)) == []


def test_due_skips_disabled_and_recently_sent(db_session):
    repo = _repo(db_session, seq=2, with_webhook=True)
    row = svc.set_schedule(db_session, repo.id, day_of_week=0, hour=9, enabled=False)
    assert svc.due_schedules(db_session, _MON_9) == []  # disabled
    row.enabled = True
    row.last_sent_at = _MON_9 - timedelta(hours=1)  # within resend window
    db_session.commit()
    assert svc.due_schedules(db_session, _MON_9) == []
    row.last_sent_at = _MON_9 - timedelta(days=7)  # long ago → due again
    db_session.commit()
    assert len(svc.due_schedules(db_session, _MON_9)) == 1


async def test_run_due_sends_and_stamps(db_session):
    repo = _repo(db_session, seq=3, with_webhook=True)
    svc.set_schedule(db_session, repo.id, day_of_week=0, hour=9, enabled=True)
    sent: list[tuple[str, dict]] = []

    async def fake_send(url, payload):
        sent.append((url, payload))

    n = await svc.run_due_digests(db_session, _MON_9, sender=fake_send)
    assert n == 1
    assert sent and sent[0][0].startswith("https://hooks.slack.com/")
    row = svc.get_schedule(db_session, repo.id)
    assert row.last_sent_at is not None
    # second run in the same window is de-duped (no resend)
    assert await svc.run_due_digests(db_session, _MON_9, sender=fake_send) == 0


async def test_run_due_skips_without_webhook_but_stamps(db_session):
    repo = _repo(db_session, seq=4, with_webhook=False)
    svc.set_schedule(db_session, repo.id, day_of_week=0, hour=9, enabled=True)
    sent: list = []

    async def fake_send(url, payload):
        sent.append(url)

    n = await svc.run_due_digests(db_session, _MON_9, sender=fake_send)
    assert n == 0 and sent == []
    # stamped so it won't be reconsidered every tick
    assert svc.get_schedule(db_session, repo.id).last_sent_at is not None


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #


def _owned_repo(db, user, seq: int) -> Repository:
    inst = GitHubInstallation(
        installation_id=9850 + seq, account_login="acme", account_type="User",
        owner_user_id=user.id,
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=9851 + seq, full_name=f"acme/e{seq}",
        default_branch="main",
    )
    db.add(repo)
    db.flush()
    return repo


def test_schedule_endpoints(authed_client, db_session):
    api_client, user = authed_client
    repo = _owned_repo(db_session, user, 0)

    assert api_client.get(f"/api/v1/repositories/{repo.id}/digest/schedule").json() == {
        "configured": False, "day_of_week": None, "hour": None,
        "enabled": False, "last_sent_at": None,
    }
    put = api_client.put(
        f"/api/v1/repositories/{repo.id}/digest/schedule",
        json={"day_of_week": 4, "hour": 15, "enabled": True},
    )
    assert put.status_code == 200
    body = put.json()
    assert body["configured"] and body["day_of_week"] == 4 and body["hour"] == 15

    got = api_client.get(f"/api/v1/repositories/{repo.id}/digest/schedule").json()
    assert got["day_of_week"] == 4 and got["enabled"] is True

    # out-of-range values rejected by validation
    bad = api_client.put(
        f"/api/v1/repositories/{repo.id}/digest/schedule",
        json={"day_of_week": 9, "hour": 15, "enabled": True},
    )
    assert bad.status_code == 422

    assert api_client.delete(f"/api/v1/repositories/{repo.id}/digest/schedule").status_code == 204
    assert (
        api_client.get(f"/api/v1/repositories/{repo.id}/digest/schedule").json()["configured"]
        is False
    )


def test_schedule_requires_auth(client):
    assert client.get("/api/v1/repositories/1/digest/schedule").status_code == 401
    put = client.put(
        "/api/v1/repositories/1/digest/schedule",
        json={"day_of_week": 1, "hour": 9, "enabled": True},
    )
    assert put.status_code == 401
