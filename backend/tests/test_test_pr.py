from __future__ import annotations

import httpx
from sqlalchemy import select

from app.models import (
    AnalysisJob,
    DriftSeverity,
    GeneratedPR,
    GitHubInstallation,
    JobStatus,
    JobType,
    Repository,
    RiskFinding,
    User,
)
from app.services.analysis.test_pr import create_test_pr
from app.services.analysis.testgen import generate_test_file
from app.services.analysis.testgen import test_path_for as build_test_path
from app.services.github.client import PullRequestResult
from tests._fakes import FakeAI
from tests.conftest import requires_db


def test_build_test_path():
    assert build_test_path("src/payment.py", "python") == "tests/test_payment_variorum.py"
    assert build_test_path("src/lib/api.ts", "typescript") == "src/lib/api.variorum.test.ts"
    assert build_test_path("index.js", "javascript") == "index.variorum.test.js"


async def test_generate_test_file_strips_fences():
    ai = FakeAI(text="```python\ndef test_charge():\n    assert True\n```")
    out = await generate_test_file(
        ai,
        source_path="src/payment.py",
        source_content="def charge(): ...",
        untested_scenarios=["duplicate charge"],
        language="python",
    )
    assert out.startswith("def test_charge")
    assert "```" not in out
    assert any("duplicate charge" in c for c in ai.calls)


class FakeGH:
    def __init__(self, source_path, *, source="def charge(): ...", pr_conflict=False):
        self.source_path = source_path
        self.source = source
        self.pr_conflict = pr_conflict
        self.put_files: list[tuple] = []
        self.prs: list[str] = []
        self.branches: list[str] = []

    async def get_file(self, _i, _f, path, _ref):
        if path == self.source_path:
            return (self.source, "sha1")
        return (None, None)

    async def get_branch_sha(self, *_a):
        return "base-sha"

    async def create_branch(self, _i, _f, branch, _sha):
        self.branches.append(branch)

    async def put_file(self, _i, _f, path, _m, content, branch, sha=None):
        self.put_files.append((path, content, branch, sha))

    async def create_pull_request(self, _i, _f, *, title, head, base, body):
        if self.pr_conflict:
            req = httpx.Request("POST", "https://api.github.com/repos/acme/app/pulls")
            raise httpx.HTTPStatusError(
                "422", request=req, response=httpx.Response(422, request=req)
            )
        self.prs.append(title)
        return PullRequestResult(number=200, url="https://gh/pr/200")

    async def find_open_pull_request(self, *_a):
        return PullRequestResult(number=201, url="https://gh/pr/201")


def _seed_finding(db, *, owner_id: int | None = None, path: str = "src/payment.py") -> RiskFinding:
    uid = owner_id
    if uid is None:
        u = User(email="tp@example.com", github_user_id=7400)
        db.add(u)
        db.flush()
        uid = u.id
    inst = GitHubInstallation(
        installation_id=8800, account_login="acme", account_type="User", owner_user_id=uid
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=8801, full_name="acme/app", default_branch="main"
    )
    db.add(repo)
    db.flush()
    job = AnalysisJob(repository_id=repo.id, type=JobType.pr_analysis, status=JobStatus.succeeded)
    db.add(job)
    db.flush()
    finding = RiskFinding(
        analysis_job_id=job.id,
        path=path,
        risk_level=DriftSeverity.high,
        summary="risky payment change",
        evidence={"pr_number": 9, "untested_scenarios": ["duplicate charge"]},
    )
    db.add(finding)
    db.flush()
    return finding


pytestmark = requires_db


async def test_create_test_pr_opens_pr(db_session):
    finding = _seed_finding(db_session)
    gh = FakeGH("src/payment.py")
    ai = FakeAI(text="def test_charge():\n    assert True\n")

    result = await create_test_pr(db_session, finding, client=gh, ai=ai)

    assert result is not None and result.pr_number == 200
    assert gh.put_files[0][0] == "tests/test_payment_variorum.py"
    assert "test_charge" in gh.put_files[0][1]
    generated = db_session.execute(
        select(GeneratedPR).where(GeneratedPR.risk_finding_id == finding.id)
    ).scalar_one()
    assert generated.pr_number == 200


async def test_create_test_pr_idempotent(db_session):
    finding = _seed_finding(db_session)
    first = await create_test_pr(
        db_session, finding, client=FakeGH("src/payment.py"), ai=FakeAI(text="t")
    )
    second = await create_test_pr(
        db_session, finding, client=FakeGH("src/payment.py"), ai=FakeAI(text="t")
    )
    assert first and second and second.reused is True


async def test_create_test_pr_missing_source_returns_none(db_session):
    finding = _seed_finding(db_session, path="src/gone.py")
    gh = FakeGH("src/other.py")  # source path won't match -> get_file returns None
    result = await create_test_pr(db_session, finding, client=gh, ai=FakeAI(text="t"))
    assert result is None


def test_generate_tests_requires_auth(client):
    assert client.post("/api/v1/risk-findings/1/generate-tests").status_code == 401
