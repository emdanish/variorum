from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Suppression(Base, TimestampMixin):
    """A user's decision to stop being re-nagged about a finding. When a finding
    is dismissed, its target is suppressed so re-analysis doesn't recreate an
    equivalent finding; restoring the finding lifts the suppression."""

    __tablename__ = "suppressions"
    __table_args__ = (
        UniqueConstraint("repository_id", "kind", "target", name="uq_suppression_repo_kind_target"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)  # "drift" | "risk"
    target: Mapped[str] = mapped_column(String(1024), nullable=False)  # doc path / file path
