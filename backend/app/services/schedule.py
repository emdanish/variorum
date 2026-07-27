from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models import DigestSchedule, GitHubInstallation, Repository, User
from app.services import digest as digest_svc
from app.services import slack as slack_svc

logger = get_logger("variorum.schedule")

# A schedule fires at most once per firing window; this guards against a tick
# re-sending within the same hour (ticks run more often than hourly).
_MIN_RESEND = timedelta(hours=12)

Sender = Callable[[str, dict], Awaitable[None]]


def get_schedule(db: Session, repository_id: int) -> DigestSchedule | None:
    return db.execute(
        select(DigestSchedule).where(DigestSchedule.repository_id == repository_id)
    ).scalar_one_or_none()


def set_schedule(
    db: Session, repository_id: int, *, day_of_week: int, hour: int, enabled: bool
) -> DigestSchedule:
    row = get_schedule(db, repository_id)
    if row is None:
        row = DigestSchedule(repository_id=repository_id)
        db.add(row)
    row.day_of_week = day_of_week
    row.hour = hour
    row.enabled = enabled
    db.commit()
    db.refresh(row)
    return row


def delete_schedule(db: Session, repository_id: int) -> bool:
    row = get_schedule(db, repository_id)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def due_schedules(db: Session, now: datetime) -> list[DigestSchedule]:
    """Enabled schedules whose UTC (weekday, hour) matches `now` and that have not
    already fired within the resend window."""
    rows = (
        db.execute(
            select(DigestSchedule).where(
                DigestSchedule.enabled.is_(True),
                DigestSchedule.day_of_week == now.weekday(),
                DigestSchedule.hour == now.hour,
            )
        )
        .scalars()
        .all()
    )
    return [r for r in rows if r.last_sent_at is None or (now - r.last_sent_at) >= _MIN_RESEND]


def _owner_webhook(db: Session, repository_id: int) -> tuple[Repository | None, str | None]:
    repo = db.get(Repository, repository_id)
    if repo is None:
        return None, None
    installation = db.get(GitHubInstallation, repo.installation_id)
    if installation is None or installation.owner_user_id is None:
        return repo, None
    owner = db.get(User, installation.owner_user_id)
    return repo, (owner.slack_webhook_url if owner else None)


async def run_due_digests(
    db: Session, now: datetime, *, sender: Sender | None = None
) -> int:
    """Deliver every due repository digest to its owner's Slack webhook. Best-effort
    per schedule — one failure never blocks the others. Returns the number sent."""
    send = sender or slack_svc.send
    sent = 0
    for schedule in due_schedules(db, now):
        try:
            repo, webhook = _owner_webhook(db, schedule.repository_id)
            if repo is None or not webhook:
                # Stamp anyway so an un-sendable schedule doesn't retry every tick.
                schedule.last_sent_at = now
                db.commit()
                continue
            digest = digest_svc.build_digest(db, repo.id, days=7)
            payload = slack_svc.build_digest_message(repo.full_name, digest)
            await send(webhook, payload)
            schedule.last_sent_at = now
            db.commit()
            sent += 1
            logger.info("scheduled digest sent repo=%s", repo.full_name)
        except Exception as exc:  # noqa: BLE001 — isolate per-schedule failures
            db.rollback()
            logger.warning(
                "scheduled digest failed repo_id=%s: %s", schedule.repository_id, exc
            )
    return sent
