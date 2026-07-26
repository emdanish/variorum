from __future__ import annotations

from app.models import (
    CodeSymbol,
    DocCodeLink,
    Document,
    GitHubInstallation,
    LinkSource,
    Repository,
    User,
)
from app.services.analysis.pr_context import build_candidates
from tests.conftest import requires_db

pytestmark = requires_db


def _seed(db):
    user = User(email="ctx@example.com", github_user_id=321)
    db.add(user)
    db.flush()
    inst = GitHubInstallation(
        installation_id=8800, account_login="acme", account_type="User", owner_user_id=user.id
    )
    db.add(inst)
    db.flush()
    repo = Repository(
        installation_id=inst.id, github_repo_id=8801, full_name="acme/app", default_branch="main"
    )
    db.add(repo)
    db.flush()

    symbol = CodeSymbol(
        repository_id=repo.id, path="src/auth.py", language="python", kind="function", name="login"
    )
    other = CodeSymbol(
        repository_id=repo.id, path="src/util.py", language="python", kind="function", name="noop"
    )
    db.add_all([symbol, other])
    db.flush()

    auth_doc = Document(repository_id=repo.id, path="docs/auth.md", title="Auth")
    other_doc = Document(repository_id=repo.id, path="docs/util.md", title="Util")
    db.add_all([auth_doc, other_doc])
    db.flush()

    # auth doc links to src/auth.py via a symbol link and a path link
    db.add(
        DocCodeLink(
            document_id=auth_doc.id,
            symbol_id=symbol.id,
            path="src/auth.py",
            confidence=0.6,
            source=LinkSource.heuristic,
        )
    )
    # util doc links only to src/util.py
    db.add(
        DocCodeLink(
            document_id=other_doc.id,
            symbol_id=other.id,
            path="src/util.py",
            confidence=0.6,
            source=LinkSource.heuristic,
        )
    )
    db.flush()
    return repo


def test_build_candidates_matches_changed_files(db_session):
    repo = _seed(db_session)
    candidates = build_candidates(db_session, repo.id, {"src/auth.py"})
    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.document_path == "docs/auth.md"
    assert candidate.trigger_paths == ["src/auth.py"]
    assert candidate.symbol_names == ["login"]


def test_build_candidates_ignores_unrelated_changes(db_session):
    repo = _seed(db_session)
    assert build_candidates(db_session, repo.id, {"src/nowhere.py"}) == []


def test_build_candidates_empty_changed_paths(db_session):
    repo = _seed(db_session)
    assert build_candidates(db_session, repo.id, set()) == []
