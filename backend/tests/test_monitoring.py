from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models import GitHubInstallation, MetricSnapshot, Repository, User
from app.services import monitoring as svc
from tests.conftest import requires_db

pytestmark = requires_db

_T0 = datetime(2026, 3, 2, 9, 0, tzinfo=UTC)


def _repo(db, user_id, seq=0) -> Repository:
    inst = GitHubInstallation(
        installation_id=9600 + seq, account_login="acme", account_type="User",
        owner_user_id=user_id,
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=9601 + seq, full_name=f"acme/m{seq}",
        default_branch="main",
    )
    db.add(repo)
    db.flush()
    return repo


def _snap(repo_id, when, **kw) -> MetricSnapshot:
    base = {
        "health_score": 80, "doc_coverage_pct": 50.0, "single_owner_modules": 1,
        "module_count": 5, "critical_hotspots": 0, "high_hotspots": 1,
        "drift_open": 0, "risk_open": 0,
    }
    base.update(kw)
    return MetricSnapshot(repository_id=repo_id, captured_at=when, **base)


# --------------------------------------------------------------------------- #
# Alert detection (pure)
# --------------------------------------------------------------------------- #


def test_detect_health_drop():
    prev = _snap(1, _T0, health_score=85)
    curr = _snap(1, _T0, health_score=70)  # -15
    alerts = svc.detect_alerts(prev, curr)
    kinds = {a["kind"] for a in alerts}
    assert "health_drop" in kinds
    hd = next(a for a in alerts if a["kind"] == "health_drop")
    assert hd["severity"] == "warning"  # 15 < 20
    # a 20+ drop is critical
    assert svc.detect_alerts(_snap(1, _T0, health_score=90), _snap(1, _T0, health_score=65))[
        0
    ]["severity"] == "critical"


def test_detect_no_alert_on_small_change_or_improvement():
    assert svc.detect_alerts(_snap(1, _T0, health_score=80), _snap(1, _T0, health_score=75)) == []
    assert svc.detect_alerts(_snap(1, _T0, health_score=70), _snap(1, _T0, health_score=90)) == []
    # from a zero baseline (no prior data) we don't cry regression
    assert svc.detect_alerts(_snap(1, _T0, health_score=0), _snap(1, _T0, health_score=0)) == []


def test_detect_new_critical_hotspot_and_single_owner():
    prev = _snap(1, _T0, critical_hotspots=0, single_owner_modules=1)
    curr = _snap(1, _T0, critical_hotspots=2, single_owner_modules=3)
    kinds = {a["kind"] for a in svc.detect_alerts(prev, curr)}
    assert kinds == {"new_critical_hotspot", "single_owner_increase"}


# --------------------------------------------------------------------------- #
# Capture + history + alert persistence
# --------------------------------------------------------------------------- #


def test_capture_records_snapshot_no_alert_first_time(db_session):
    u = User(email="mon0@example.com", github_user_id=9600)
    db_session.add(u)
    db_session.flush()
    repo = _repo(db_session, u.id, 0)
    snap, alerts = svc.capture(db_session, repo.id, _T0)
    assert snap.id is not None
    assert alerts == []  # nothing to compare against
    assert len(svc.history(db_session, repo.id)) == 1


def test_capture_raises_alert_on_regression(db_session):
    u = User(email="mon1@example.com", github_user_id=9601)
    db_session.add(u)
    db_session.flush()
    repo = _repo(db_session, u.id, 1)
    # seed a healthy prior snapshot by hand, then capture a worse one
    db_session.add(_snap(repo.id, _T0 - timedelta(days=1), health_score=90, critical_hotspots=0))
    db_session.flush()
    # monkeypatch compute_metrics to a regressed state
    import app.services.monitoring as m

    orig = m.compute_metrics
    m.compute_metrics = lambda db, rid: {  # type: ignore[assignment]
        "health_score": 60, "doc_coverage_pct": 40.0, "single_owner_modules": 1,
        "module_count": 5, "critical_hotspots": 1, "high_hotspots": 1,
        "drift_open": 0, "risk_open": 0,
    }
    try:
        snap, alerts = svc.capture(db_session, repo.id, _T0)
    finally:
        m.compute_metrics = orig
    kinds = {a.kind for a in alerts}
    assert "health_drop" in kinds and "new_critical_hotspot" in kinds
    # persisted + surfaced as unacknowledged
    open_alerts = svc.list_alerts(db_session, repo.id)
    assert len(open_alerts) == len(alerts)


def test_history_oldest_to_newest(db_session):
    u = User(email="mon2@example.com", github_user_id=9602)
    db_session.add(u)
    db_session.flush()
    repo = _repo(db_session, u.id, 2)
    db_session.add_all(
        [
            _snap(repo.id, _T0),
            _snap(repo.id, _T0 + timedelta(days=1)),
            _snap(repo.id, _T0 + timedelta(days=2)),
        ]
    )
    db_session.flush()
    hist = svc.history(db_session, repo.id)
    assert [h.captured_at for h in hist] == sorted(h.captured_at for h in hist)


# --------------------------------------------------------------------------- #
# Acknowledge + per-user feed
# --------------------------------------------------------------------------- #


def test_acknowledge_and_user_feed(db_session):
    u = User(email="mon3@example.com", github_user_id=9603)
    db_session.add(u)
    db_session.flush()
    repo = _repo(db_session, u.id, 3)
    db_session.add(_snap(repo.id, _T0 - timedelta(days=1), health_score=95))
    db_session.flush()
    import app.services.monitoring as m

    orig = m.compute_metrics
    m.compute_metrics = lambda db, rid: {  # type: ignore[assignment]
        "health_score": 60, "doc_coverage_pct": 40.0, "single_owner_modules": 1,
        "module_count": 5, "critical_hotspots": 0, "high_hotspots": 1,
        "drift_open": 0, "risk_open": 0,
    }
    try:
        _, alerts = svc.capture(db_session, repo.id, _T0)
    finally:
        m.compute_metrics = orig
    assert alerts
    feed = svc.list_alerts_for_user(db_session, u.id)
    assert len(feed) == len(alerts)

    assert svc.acknowledge(db_session, repo.id, alerts[0].id, _T0) is True
    assert len(svc.list_alerts_for_user(db_session, u.id)) == len(alerts) - 1
    # bad id → False
    assert svc.acknowledge(db_session, repo.id, 999999, _T0) is False


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #


def test_trends_and_snapshot_endpoints(authed_client, db_session):
    api_client, user = authed_client
    repo = _repo(db_session, user.id, 4)
    db_session.flush()
    # empty at first
    assert api_client.get(f"/api/v1/repositories/{repo.id}/trends").json()["snapshots"] == []
    # capture now
    resp = api_client.post(f"/api/v1/repositories/{repo.id}/snapshot")
    assert resp.status_code == 200 and resp.json()["captured"] is True
    trends = api_client.get(f"/api/v1/repositories/{repo.id}/trends").json()
    assert len(trends["snapshots"]) == 1


def test_alerts_endpoints_and_ack(authed_client, db_session):
    api_client, user = authed_client
    repo = _repo(db_session, user.id, 5)
    db_session.add(_snap(repo.id, _T0 - timedelta(days=1), health_score=95))
    db_session.flush()
    import app.services.monitoring as m

    orig = m.compute_metrics
    m.compute_metrics = lambda db, rid: {  # type: ignore[assignment]
        "health_score": 60, "doc_coverage_pct": 40.0, "single_owner_modules": 1,
        "module_count": 5, "critical_hotspots": 0, "high_hotspots": 1,
        "drift_open": 0, "risk_open": 0,
    }
    try:
        api_client.post(f"/api/v1/repositories/{repo.id}/snapshot")
    finally:
        m.compute_metrics = orig

    alerts = api_client.get(f"/api/v1/repositories/{repo.id}/alerts").json()
    assert alerts and alerts[0]["kind"] == "health_drop"
    # global feed
    feed = api_client.get("/api/v1/alerts").json()
    assert any(a["repository_id"] == repo.id for a in feed)
    # ack
    aid = alerts[0]["id"]
    assert api_client.post(f"/api/v1/repositories/{repo.id}/alerts/{aid}/ack").status_code == 204
    assert api_client.get(f"/api/v1/repositories/{repo.id}/alerts").json() == []


def test_monitoring_requires_auth(client):
    assert client.get("/api/v1/repositories/1/trends").status_code == 401
    assert client.post("/api/v1/repositories/1/snapshot").status_code == 401
    assert client.get("/api/v1/repositories/1/alerts").status_code == 401
    assert client.get("/api/v1/alerts").status_code == 401
