from __future__ import annotations

from datetime import UTC, datetime

from app.models import (
    AnalysisJob,
    CodeSymbol,
    DecisionEntry,
    Document,
    DriftFinding,
    DriftSeverity,
    FindingStatus,
    GitHubInstallation,
    JobStatus,
    JobTrigger,
    JobType,
    KnowledgeEntry,
    KnowledgeKind,
    Repository,
    RiskFinding,
    User,
)
from app.services import contradictions as contra_svc
from app.services import digest as digest_svc
from app.services import search as search_svc
from app.services.github.client import ChangedFile
from tests._fakes import FakeAI
from tests.conftest import requires_db

pytestmark = requires_db


def _repo(db, user_id, seq=0):
    inst = GitHubInstallation(
        installation_id=9300 + seq, account_login="acme", account_type="User",
        owner_user_id=user_id,
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=9301 + seq, full_name=f"acme/x{seq}",
        default_branch="main",
    )
    db.add(repo)
    db.flush()
    return repo


# --------------------------------------------------------------------------- #
# Unified search
# --------------------------------------------------------------------------- #


def test_unified_search(db_session):
    u = User(email="s@example.com", github_user_id=9300)
    db_session.add(u)
    db_session.flush()
    repo = _repo(db_session, u.id)
    db_session.add_all(
        [
            CodeSymbol(repository_id=repo.id, path="src/payment.py", language="python",
                       kind="function", name="charge_payment"),
            Document(repository_id=repo.id, path="docs/payment.md", title="Payment guide"),
            DecisionEntry(repository_id=repo.id, title="Payment provider choice",
                          summary="Chose Stripe for payment.", sources=[]),
            KnowledgeEntry(repository_id=repo.id, kind=KnowledgeKind.pull_request,
                           source_ref="42", title="Add payment retries"),
        ]
    )
    db_session.flush()

    res = search_svc.unified_search(db_session, repo.id, "payment")
    assert res["total"] == 4
    assert res["symbols"][0]["name"] == "charge_payment"
    assert res["documents"][0]["path"] == "docs/payment.md"
    assert res["decisions"][0]["title"] == "Payment provider choice"
    assert res["knowledge"][0]["source_ref"] == "42"


def test_search_endpoint(authed_client, db_session):
    api_client, user = authed_client
    repo = _repo(db_session, user.id, seq=1)
    db_session.add(
        CodeSymbol(repository_id=repo.id, path="src/auth.py", language="python",
                   kind="function", name="login")
    )
    db_session.flush()
    resp = api_client.get(f"/api/v1/repositories/{repo.id}/search", params={"q": "login"})
    assert resp.status_code == 200
    assert resp.json()["symbols"][0]["name"] == "login"
    # too-short query is rejected by validation
    assert api_client.get(
        f"/api/v1/repositories/{repo.id}/search", params={"q": "a"}
    ).status_code == 422


def test_search_requires_auth(client):
    assert client.get("/api/v1/repositories/1/search", params={"q": "abc"}).status_code == 401


# --------------------------------------------------------------------------- #
# Weekly digest
# --------------------------------------------------------------------------- #


def test_digest(db_session):
    u = User(email="dg@example.com", github_user_id=9310)
    db_session.add(u)
    db_session.flush()
    repo = _repo(db_session, u.id, seq=2)
    job = AnalysisJob(repository_id=repo.id, type=JobType.pr_analysis, status=JobStatus.succeeded,
                      trigger=JobTrigger.manual)
    db_session.add(job)
    db_session.flush()
    db_session.add_all(
        [
            DriftFinding(analysis_job_id=job.id, severity=DriftSeverity.high, summary="d",
                         evidence={}, status=FindingStatus.detected),
            RiskFinding(analysis_job_id=job.id, path="a.py", risk_level=DriftSeverity.high,
                        summary="r", evidence={}),
            KnowledgeEntry(repository_id=repo.id, kind=KnowledgeKind.commit, source_ref="c1",
                           title="recent commit"),
            DecisionEntry(repository_id=repo.id, title="Dec", summary="s", sources=[]),
        ]
    )
    db_session.flush()

    d = digest_svc.build_digest(db_session, repo.id, days=7)
    assert d["new_drift"] == 1
    assert d["new_risk"] == 1
    assert d["new_knowledge"] == 1
    assert d["decisions_total"] == 1
    assert 0 <= d["health_score"] <= 100
    assert isinstance(d["top_hotspots"], list)


def test_digest_endpoint(authed_client, db_session):
    api_client, user = authed_client
    repo = _repo(db_session, user.id, seq=3)
    db_session.flush()
    resp = api_client.get(f"/api/v1/repositories/{repo.id}/digest", params={"days": 14})
    assert resp.status_code == 200
    assert resp.json()["days"] == 14


def test_digest_requires_auth(client):
    assert client.get("/api/v1/repositories/1/digest").status_code == 401


# --------------------------------------------------------------------------- #
# Contradiction detection
# --------------------------------------------------------------------------- #


def _entry():
    return KnowledgeEntry(
        repository_id=1, kind=KnowledgeKind.pull_request, source_ref="182",
        title="Use Redis queues", body="All async work must go through Redis.",
        url="http://x/182", occurred_at=datetime(2026, 3, 1, tzinfo=UTC),
    )


def test_contradiction_parse_and_check():
    entries = [_entry()]
    data = {"contradictions": [{"cited": 1, "explanation": "Sends email inline, not via Redis."}]}
    parsed = contra_svc.parse(data, entries)
    assert len(parsed) == 1
    assert parsed[0]["source"]["source_ref"] == "182"
    assert "Redis" in parsed[0]["explanation"]
    # bad citations / garbage are dropped
    assert contra_svc.parse({"contradictions": [{"cited": 9, "explanation": "x"}]}, entries) == []
    assert contra_svc.parse({}, entries) == []


async def test_check_contradictions_empty_without_entries():
    fake = FakeAI(verdict={"contradictions": []})
    assert await contra_svc.check_contradictions(fake, "some change", []) == []


def test_contradictions_endpoint(authed_client, db_session, monkeypatch):
    api_client, user = authed_client
    repo = _repo(db_session, user.id, seq=4)
    entry = KnowledgeEntry(
        repository_id=repo.id, kind=KnowledgeKind.pull_request, source_ref="9",
        title="Async via Redis", body="Async work goes through Redis.", url="http://x/9",
    )
    db_session.add(entry)
    db_session.flush()

    fake = FakeAI(
        verdict={"contradictions": [{"cited": 1, "explanation": "Adds inline email send."}]}
    )

    async def fake_files(self, installation_id, full_name, number):
        return [
            ChangedFile(path="src/mail.py", status="modified",
                        patch="+ send_email_inline()", additions=2, deletions=0)
        ]

    monkeypatch.setattr("app.api.routes.repositories.get_ai_service", lambda: fake)
    monkeypatch.setattr("app.api.routes.repositories.get_github_auth", lambda: object())
    monkeypatch.setattr(
        "app.api.routes.repositories.GitHubClient.list_pull_request_files", fake_files
    )
    monkeypatch.setattr(
        "app.api.routes.repositories.retrieve", lambda db, rid, text, embedder=None: [entry]
    )

    resp = api_client.get(f"/api/v1/repositories/{repo.id}/contradictions/7")
    assert resp.status_code == 200
    data = resp.json()
    assert data["pr_number"] == 7
    assert len(data["contradictions"]) == 1
    assert data["contradictions"][0]["source"]["source_ref"] == "9"


def test_contradictions_requires_auth(client):
    assert client.get("/api/v1/repositories/1/contradictions/1").status_code == 401
