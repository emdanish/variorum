from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Suppression

DRIFT = "drift"
RISK = "risk"


def suppress(db: Session, repository_id: int, kind: str, target: str) -> None:
    """Record that the user doesn't want to be re-nagged about `target`. Idempotent."""
    if not target:
        return
    exists = db.execute(
        select(Suppression.id).where(
            Suppression.repository_id == repository_id,
            Suppression.kind == kind,
            Suppression.target == target,
        )
    ).scalar_one_or_none()
    if exists is None:
        db.add(Suppression(repository_id=repository_id, kind=kind, target=target))
        db.commit()


def unsuppress(db: Session, repository_id: int, kind: str, target: str) -> None:
    """Lift a suppression (e.g. when a finding is restored) so it can surface again."""
    if not target:
        return
    db.execute(
        delete(Suppression).where(
            Suppression.repository_id == repository_id,
            Suppression.kind == kind,
            Suppression.target == target,
        )
    )
    db.commit()


def suppressed_targets(db: Session, repository_id: int, kind: str) -> set[str]:
    """Active suppression targets for a repo/kind — used to skip creating
    equivalent findings during re-analysis."""
    return set(
        db.execute(
            select(Suppression.target).where(
                Suppression.repository_id == repository_id, Suppression.kind == kind
            )
        )
        .scalars()
        .all()
    )
