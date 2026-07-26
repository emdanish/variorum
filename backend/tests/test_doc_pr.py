from __future__ import annotations

from sqlalchemy import func, select

from app.models import (
    AnalysisJob,
    Document,
    DriftFinding,
    DriftSeverity,
    FindingStatus,
    GeneratedPR,
    GitHubInstallation,
    JobStatus,
    JobType,
    Repository,
    User,
)
from app.services.analysis.doc_pr import create_doc_fix_pr
from app.services.github.client import PullRequestResult
from tests._fakes import FakeAI
from tests.conftest import requires_db

pytestmark = requires_db


class FakeGitHubClient:
    def __init__(self, *, file_content: str | None = "# Auth\n\nUses cookies.\n"):
        self.file_content = file_content
        self.created_branches: list[tuple[str, str]] = []
        self.put_files: list[tuple[str, str, str, str | None]] = []
        self.prs: list[dict] = []

    async def get_file(self, _inst, _full, _path, _ref):
        return (self.file_content, "blob-sha" if self.file_content is not None else None)

    async def get_branch_sha(self, _inst, _full, _branch):
        return "base-sha"

    async def create_branch(self, _inst, _full, branch, base_sha):
        self.created_branches.append((branch, base_sha))

    async def put_file(self, _inst, _full, path, _message, content, branch, sha=None):
        self.put_files.append((path, content, branch, sha))

    async def create_pull_request(self, _inst, _full, *, title, head, base, body):
        self.prs.append({"title": title, "head": head, "base": base, "body": body})
        return PullRequestResult(number=101, url="https://github.com/acme/app/pull/101")


def _seed_finding(db, *, summary="Auth switched to JWT") -> DriftFinding:
    user = User(email="pr4@example.com", github_user_id=444)
    db.add(user)
    db.flush()
    inst = GitHubInstallation(
        installation_id=4400, account_login="acme", account_type="User", owner_user_id=user.id
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=4401, full_name="acme/app", default_branch="main"
    )
    db.add(repo)
    db.flush()
    doc = Document(repository_id=repo.id, path="docs/auth.md", title="Auth")
    db.add(doc)
    db.flush()
    job = AnalysisJob(
        repository_id=repo.id, type=JobType.pr_analysis, status=JobStatus.succeeded
    )
    db.add(job)
    db.flush()
    finding = DriftFinding(
        analysis_job_id=job.id,
        document_id=doc.id,
        severity=DriftSeverity.high,
        summary=summary,
        status=FindingStatus.detected,
        evidence={
            "pr_number": 42,
            "document_path": "docs/auth.md",
            "suggested_update": "Describe JWT",
            "drift_evidence": ["diff shows jwt"],
            "provider": "gemini-1",
            "model": "gemini-test",
        },
    )
    db.add(finding)
    db.flush()
    return finding


async def test_create_doc_fix_pr_opens_pr(db_session):
    finding = _seed_finding(db_session)
    client = FakeGitHubClient()
    ai = FakeAI(text="# Auth\n\nUses JWT tokens.\n")

    result = await create_doc_fix_pr(db_session, finding, client=client, ai=ai)

    assert result is not None
    assert result.pr_number == 101
    assert result.branch == f"variorum/doc-fix-{finding.id}"
    assert result.url == "https://github.com/acme/app/pull/101"

    assert len(client.created_branches) == 1
    assert client.put_files[0][0] == "docs/auth.md"
    assert "JWT" in client.put_files[0][1]
    assert len(client.prs) == 1

    db_session.refresh(finding)
    assert finding.status == FindingStatus.pr_opened
    generated = db_session.execute(
        select(GeneratedPR).where(GeneratedPR.drift_finding_id == finding.id)
    ).scalar_one()
    assert generated.pr_number == 101


async def test_create_doc_fix_pr_is_idempotent(db_session):
    finding = _seed_finding(db_session)
    client = FakeGitHubClient()
    ai = FakeAI(text="# Auth\n\nUses JWT tokens.\n")

    first = await create_doc_fix_pr(db_session, finding, client=client, ai=ai)
    second = await create_doc_fix_pr(db_session, finding, client=FakeGitHubClient(), ai=ai)

    assert first is not None and second is not None
    assert second.reused is True
    count = db_session.scalar(
        select(func.count())
        .select_from(GeneratedPR)
        .where(GeneratedPR.drift_finding_id == finding.id)
    )
    assert count == 1


async def test_create_doc_fix_pr_no_change_returns_none(db_session):
    finding = _seed_finding(db_session)
    current = "# Auth\n\nUses cookies.\n"
    client = FakeGitHubClient(file_content=current)
    ai = FakeAI(text=current)  # model returns identical content

    result = await create_doc_fix_pr(db_session, finding, client=client, ai=ai)

    assert result is None
    assert client.prs == []
    db_session.refresh(finding)
    assert finding.status == FindingStatus.detected


async def test_create_doc_fix_pr_missing_doc_returns_none(db_session):
    finding = _seed_finding(db_session)
    client = FakeGitHubClient(file_content=None)  # doc not present on base branch
    ai = FakeAI(text="whatever")

    result = await create_doc_fix_pr(db_session, finding, client=client, ai=ai)
    assert result is None
    assert client.prs == []
