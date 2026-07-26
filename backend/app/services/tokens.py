from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ApiToken, User

_PREFIX = "vrm_"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate() -> tuple[str, str, str]:
    """Return (plaintext, display_prefix, token_hash) for a fresh token."""
    token = _PREFIX + secrets.token_urlsafe(32)
    return token, token[:12], _hash(token)


def create_token(db: Session, user_id: int, name: str) -> tuple[ApiToken, str]:
    plaintext, prefix, token_hash = generate()
    row = ApiToken(user_id=user_id, name=name.strip()[:120] or "token", prefix=prefix,
                   token_hash=token_hash)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, plaintext


def list_tokens(db: Session, user_id: int) -> list[ApiToken]:
    return list(
        db.execute(
            select(ApiToken)
            .where(ApiToken.user_id == user_id)
            .order_by(ApiToken.created_at.desc())
        )
        .scalars()
        .all()
    )


def revoke_token(db: Session, user_id: int, token_id: int) -> bool:
    row = db.execute(
        select(ApiToken).where(ApiToken.id == token_id, ApiToken.user_id == user_id)
    ).scalar_one_or_none()
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def resolve_token(db: Session, token: str) -> User | None:
    """Resolve a bearer token to its user, stamping last-used. Returns None if
    the token is malformed or unknown."""
    if not token or not token.startswith(_PREFIX):
        return None
    row = db.execute(
        select(ApiToken).where(ApiToken.token_hash == _hash(token))
    ).scalar_one_or_none()
    if row is None:
        return None
    row.last_used_at = datetime.now(UTC)
    db.commit()
    return db.get(User, row.user_id)
