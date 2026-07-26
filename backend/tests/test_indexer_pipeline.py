from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.models import (
    CodeSymbol,
    DocCodeLink,
    Document,
    GitHubInstallation,
    IndexingStatus,
    JobStatus,
    Repository,
    User,
)
from app.services.indexer.pipeline import reindex_repository
from app.workers.indexing import run_index_job
from tests.conftest import requires_db

pytestmark = requires_db


def _seed_repo(db) -> Repository:
    user = User(email="idx@example.com", name="Idx", github_user_id=555)
    db.add(user)
    db.flush()
    inst = GitHubInstallation(
        installation_id=9100,
        account_login="acme",
        account_type="Organization",
        owner_user_id=user.id,
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id,
        github_repo_id=9101,
        full_name="acme/sample",
        default_branch="main",
        private=True,
    )
    db.add(repo)
    db.flush()
    return repo


def _count(db, model, repo_id) -> int:
    return db.scalar(
        select(func.count()).select_from(model).where(model.repository_id == repo_id)
    )


def test_reindex_persists_symbols_docs_links(db_session, sample_repo):
    repo = _seed_repo(db_session)
    result = reindex_repository(db_session, repo, sample_repo)

    assert result.symbols > 0
    assert result.documents == 1
    assert result.links > 0

    names = set(
        db_session.execute(
            select(CodeSymbol.name).where(CodeSymbol.repository_id == repo.id)
        ).scalars()
    )
    assert {"Widget", "render", "helper", "doThing", "Thing"} <= names

    doc = db_session.execute(
        select(Document).where(Document.repository_id == repo.id)
    ).scalar_one()
    assert doc.title == "Sample Project"

    # A link to src/app.py (path mention) must exist.
    link_paths = set(
        db_session.execute(
            select(DocCodeLink.path).where(DocCodeLink.document_id == doc.id)
        ).scalars()
    )
    assert "src/app.py" in link_paths


def test_reindex_is_idempotent(db_session, sample_repo):
    repo = _seed_repo(db_session)
    first = reindex_repository(db_session, repo, sample_repo)
    second = reindex_repository(db_session, repo, sample_repo)
    assert (first.symbols, first.documents) == (second.symbols, second.documents)
    assert _count(db_session, CodeSymbol, repo.id) == second.symbols
    assert _count(db_session, Document, repo.id) == second.documents


def test_run_index_job_marks_indexed(db_session, sample_repo):
    from app.models import AnalysisJob, JobType

    repo = _seed_repo(db_session)
    result = run_index_job(repo.id, db=db_session, source_root=sample_repo)
    assert result is not None

    db_session.refresh(repo)
    assert repo.indexing_status == IndexingStatus.indexed
    assert repo.last_indexed_at is not None

    job = db_session.execute(
        select(AnalysisJob).where(AnalysisJob.repository_id == repo.id)
    ).scalar_one()
    assert job.type == JobType.indexing
    assert job.status == JobStatus.succeeded
    assert job.finished_at is not None


def test_run_index_job_records_failure(db_session, sample_repo):
    repo = _seed_repo(db_session)

    def boom(_db, _repo, _root):
        raise RuntimeError("kaboom")

    result = run_index_job(repo.id, db=db_session, source_root=sample_repo, indexer=boom)
    assert result is None

    db_session.refresh(repo)
    assert repo.indexing_status == IndexingStatus.failed

    from app.models import AnalysisJob

    job = db_session.execute(
        select(AnalysisJob).where(AnalysisJob.repository_id == repo.id)
    ).scalar_one()
    assert job.status == JobStatus.failed
    assert job.error and "kaboom" in job.error


@pytest.mark.parametrize("missing_id", [10_000_000])
def test_run_index_job_missing_repo_returns_none(db_session, missing_id):
    assert run_index_job(missing_id, db=db_session) is None
