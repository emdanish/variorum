from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.services.github.oauth import GitHubUser


def upsert_user_from_github(db: Session, gh: GitHubUser) -> User:
    user = db.execute(
        select(User).where(User.github_user_id == gh.github_user_id)
    ).scalar_one_or_none()

    if user is None and gh.email:
        user = db.execute(select(User).where(User.email == gh.email)).scalar_one_or_none()

    if user is None:
        user = User(
            github_user_id=gh.github_user_id,
            email=gh.email or f"{gh.login}@users.noreply.github.com",
            name=gh.name or gh.login,
            avatar_url=gh.avatar_url,
        )
        db.add(user)
    else:
        user.github_user_id = gh.github_user_id
        if gh.email:
            user.email = gh.email
        user.name = gh.name or gh.login
        user.avatar_url = gh.avatar_url

    db.commit()
    db.refresh(user)
    return user
