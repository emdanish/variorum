from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.services.github.oauth import GitHubUser


def upsert_user_from_github(db: Session, gh: GitHubUser) -> User:
    # Identity is keyed strictly on the stable GitHub user id. We deliberately do
    # NOT fall back to matching by email: GitHub emails can be unverified or
    # shared (incl. the noreply fallback), so matching on them would let one
    # GitHub identity take over another's account and installations.
    user = db.execute(
        select(User).where(User.github_user_id == gh.github_user_id)
    ).scalar_one_or_none()

    if user is None:
        user = User(
            github_user_id=gh.github_user_id,
            github_login=gh.login,
            email=gh.email or f"{gh.login}@users.noreply.github.com",
            name=gh.name or gh.login,
            avatar_url=gh.avatar_url,
        )
        db.add(user)
    else:
        user.github_user_id = gh.github_user_id
        user.github_login = gh.login
        if gh.email:
            user.email = gh.email
        user.name = gh.name or gh.login
        user.avatar_url = gh.avatar_url

    db.commit()
    db.refresh(user)
    return user
