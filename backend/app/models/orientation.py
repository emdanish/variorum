from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class RepositoryGuide(Base, TimestampMixin):
    """An auto-generated, cited orientation guide for a repository — what it is,
    its key areas, where to start, and the decisions behind it. One per
    repository; regenerating replaces the row (``updated_at`` marks freshness)."""

    __tablename__ = "repository_guides"

    id: Mapped[int] = mapped_column(primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    # Structured sections: key_areas[], getting_started[], decisions[], conventions[].
    content: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(128))
