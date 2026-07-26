from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta

# Penalty per open documentation-drift finding, weighted by severity. The
# documentation-health score starts at 100 and subtracts these, floored at 0.
_SEVERITY_WEIGHTS = {"high": 15, "medium": 8, "low": 3, "info": 1}
_SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1, "info": 0}


def doc_health_score(open_by_severity: dict[str, int]) -> int:
    """A 0–100 documentation-health score from open drift counts by severity."""
    penalty = sum(_SEVERITY_WEIGHTS.get(sev, 0) * count for sev, count in open_by_severity.items())
    return max(0, 100 - penalty)


def severity_rank(level: str) -> int:
    return _SEVERITY_RANK.get(level, 0)


def activity_series(
    drift_dates: list[datetime],
    risk_dates: list[datetime],
    *,
    days: int,
    now: datetime,
) -> list[dict[str, object]]:
    """Per-day counts of drift and risk findings over the trailing window."""
    drift_by_day = Counter(d.date().isoformat() for d in drift_dates if d is not None)
    risk_by_day = Counter(d.date().isoformat() for d in risk_dates if d is not None)
    series: list[dict[str, object]] = []
    start = now.date()
    for offset in range(days - 1, -1, -1):
        day = (start - timedelta(days=offset)).isoformat()
        series.append(
            {"date": day, "drift": drift_by_day.get(day, 0), "risk": risk_by_day.get(day, 0)}
        )
    return series
