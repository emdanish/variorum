from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models import User
from app.services import credits
from tests.conftest import requires_db

pytestmark = requires_db

_LIMIT = 10
_WINDOW = 3600  # 1h


def _make_user(db, n: int = 1) -> User:
    user = User(email=f"credit{n}@example.com", name="Credit", github_user_id=800000 + n)
    db.add(user)
    db.flush()
    return user


def test_new_user_starts_with_full_balance(db_session):
    user = _make_user(db_session)
    bal = credits.balance(db_session, user.id, limit=_LIMIT, window_seconds=_WINDOW)
    assert (bal.limit, bal.used, bal.remaining) == (_LIMIT, 0, _LIMIT)


def test_consume_decrements_remaining(db_session):
    user = _make_user(db_session)
    credits.consume(db_session, user.id, limit=_LIMIT, window_seconds=_WINDOW, amount=3)
    bal = credits.balance(db_session, user.id, limit=_LIMIT, window_seconds=_WINDOW)
    assert bal.used == 3
    assert bal.remaining == _LIMIT - 3


def test_remaining_never_negative(db_session):
    user = _make_user(db_session)
    credits.consume(db_session, user.id, limit=_LIMIT, window_seconds=_WINDOW, amount=99)
    bal = credits.balance(db_session, user.id, limit=_LIMIT, window_seconds=_WINDOW)
    assert bal.used == _LIMIT
    assert bal.remaining == 0


def test_window_rolls_over_after_expiry(db_session):
    user = _make_user(db_session)
    t0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    credits.consume(db_session, user.id, limit=_LIMIT, window_seconds=_WINDOW, amount=4, now=t0)

    # Still inside the window — usage persists.
    mid = credits.balance(
        db_session, user.id, limit=_LIMIT, window_seconds=_WINDOW, now=t0 + timedelta(minutes=30)
    )
    assert mid.used == 4

    # After the window elapses — the meter resets automatically.
    later = credits.balance(
        db_session, user.id, limit=_LIMIT, window_seconds=_WINDOW, now=t0 + timedelta(hours=2)
    )
    assert later.used == 0
    assert later.remaining == _LIMIT
    # resets_at is anchored to the new period, not the old one.
    assert later.resets_at > t0 + timedelta(hours=2)


def test_balance_reports_reset_time(db_session):
    user = _make_user(db_session)
    t0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    bal = credits.consume(db_session, user.id, limit=_LIMIT, window_seconds=_WINDOW, now=t0)
    assert bal.resets_at == t0 + timedelta(seconds=_WINDOW)


def test_global_meter_accumulates_across_calls_and_rolls(db_session):
    t0 = datetime(2026, 2, 1, 9, 0, tzinfo=UTC)
    credits.consume_global(db_session, limit=100, window_seconds=_WINDOW, amount=5, now=t0)
    credits.consume_global(db_session, limit=100, window_seconds=_WINDOW, amount=2, now=t0)

    inside = credits.global_balance(
        db_session, limit=100, window_seconds=_WINDOW, now=t0 + timedelta(minutes=10)
    )
    assert inside.used == 7
    assert inside.remaining == 93

    rolled = credits.global_balance(
        db_session, limit=100, window_seconds=_WINDOW, now=t0 + timedelta(hours=2)
    )
    assert rolled.used == 0
    assert rolled.remaining == 100
