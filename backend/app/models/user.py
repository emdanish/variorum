from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.github import GitHubInstallation


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(1024))
    github_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True)
    # Optional Slack incoming-webhook URL for digest delivery.
    slack_webhook_url: Mapped[str | None] = mapped_column(String(512))

    installations: Mapped[list["GitHubInstallation"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
