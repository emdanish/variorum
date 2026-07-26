from __future__ import annotations

from sqlalchemy import select

from app.models import Repository, User
from app.services.github.client import RepoInfo
from app.services.installations import (
    prune_repositories,
    remove_repositories,
    upsert_installation,
    upsert_repository,
)
from tests.conftest import requires_db

pytestmark = requires_db


def _repo(gid: int, name: str) -> RepoInfo:
    return RepoInfo(github_repo_id=gid, full_name=name, default_branch="main", private=True)


def test_upsert_installation_creates_then_updates(db_session):
    inst = upsert_installation(
        db_session, installation_id=1, account_login="acme", account_type="Organization"
    )
    assert inst.id is not None
    assert inst.suspended_at is None

    again = upsert_installation(
        db_session,
        installation_id=1,
        account_login="acme-renamed",
        account_type="Organization",
        suspended=True,
    )
    assert again.id == inst.id
    assert again.account_login == "acme-renamed"
    assert again.suspended_at is not None


def test_upsert_installation_preserves_owner_when_not_provided(db_session):
    user = User(email="owner@example.com", name="Owner", github_user_id=777)
    db_session.add(user)
    db_session.flush()

    upsert_installation(
        db_session, installation_id=2, account_login="a", account_type="User", owner_user_id=None
    )
    inst = upsert_installation(
        db_session,
        installation_id=2,
        account_login="a",
        account_type="User",
        owner_user_id=user.id,
    )
    assert inst.owner_user_id == user.id
    # A later sync without an owner must not wipe the link.
    inst = upsert_installation(
        db_session, installation_id=2, account_login="a", account_type="User"
    )
    assert inst.owner_user_id == user.id


def test_upsert_installation_does_not_reassign_to_different_owner(db_session):
    u1 = User(email="owner1@example.com", github_user_id=1001)
    u2 = User(email="owner2@example.com", github_user_id=1002)
    db_session.add_all([u1, u2])
    db_session.flush()

    upsert_installation(
        db_session, installation_id=99, account_login="a", account_type="User",
        owner_user_id=u1.id,
    )
    # A second user must not be able to claim an installation owned by u1.
    inst = upsert_installation(
        db_session, installation_id=99, account_login="a", account_type="User",
        owner_user_id=u2.id,
    )
    assert inst.owner_user_id == u1.id


def test_upsert_repository_is_idempotent(db_session):
    inst = upsert_installation(
        db_session, installation_id=3, account_login="a", account_type="User"
    )
    upsert_repository(db_session, inst, _repo(100, "a/one"))
    upsert_repository(db_session, inst, _repo(100, "a/one-renamed"))
    rows = db_session.execute(
        select(Repository).where(Repository.installation_id == inst.id)
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].full_name == "a/one-renamed"


def test_prune_removes_repositories_not_in_keep_set(db_session):
    inst = upsert_installation(
        db_session, installation_id=4, account_login="a", account_type="User"
    )
    upsert_repository(db_session, inst, _repo(1, "a/x"))
    upsert_repository(db_session, inst, _repo(2, "a/y"))
    removed = prune_repositories(db_session, inst, {1})
    assert removed == 1
    remaining = db_session.execute(
        select(Repository.github_repo_id).where(Repository.installation_id == inst.id)
    ).scalars().all()
    assert remaining == [1]


def test_remove_repositories(db_session):
    inst = upsert_installation(
        db_session, installation_id=5, account_login="a", account_type="User"
    )
    upsert_repository(db_session, inst, _repo(1, "a/x"))
    upsert_repository(db_session, inst, _repo(2, "a/y"))
    remove_repositories(db_session, inst, [2])
    remaining = db_session.execute(
        select(Repository.github_repo_id).where(Repository.installation_id == inst.id)
    ).scalars().all()
    assert remaining == [1]
