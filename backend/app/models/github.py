from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import IndexingStatus

if TYPE_CHECKING:
    from app.models.user import User


class GitHubInstallation(Base, TimestampMixin):
    __tablename__ = "github_installations"

    id: Mapped[int] = mapped_column(primary_key=True)
    installation_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    account_login: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(32), nullable=False, default="User")
    owner_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    owner: Mapped["User | None"] = relationship(back_populates="installations")
    repositories: Mapped[list["Repository"]] = relationship(
        back_populates="installation", cascade="all, delete-orphan"
    )


class Repository(Base, TimestampMixin):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True)
    installation_id: Mapped[int] = mapped_column(
        ForeignKey("github_installations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    github_repo_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, index=True, nullable=False
    )
    full_name: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    default_branch: Mapped[str] = mapped_column(String(255), nullable=False, default="main")
    private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    indexing_status: Mapped[IndexingStatus] = mapped_column(
        default=IndexingStatus.pending, nullable=False
    )
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Opt-in: when true, Variorum auto-posts a PR impact briefing comment on
    # pull_request webhooks. Off by default — posting to GitHub is outward-facing,
    # so it never happens without the owner enabling it (manual posts stay
    # available regardless).
    pr_comments_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    installation: Mapped["GitHubInstallation"] = relationship(back_populates="repositories")
