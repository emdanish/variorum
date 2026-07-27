# 5. Metric snapshots as the basis for trends and alerts

- **Status:** Accepted
- **Date:** 2026-07-27

## Context

Every knowledge-health metric (health score, doc coverage, ownership,
hotspots, findings) was point-in-time only — computed on demand, never
retained. Two requested capabilities both need history: trend charts ("are we
getting better or worse?") and regression alerts ("health just dropped"). Both
reduce to the same missing primitive: a stored time series.

## Decision

Introduce one **`MetricSnapshot`** table — a periodic capture of a repository's
current metrics — and derive both features from it:

- **Trends (4D)** read the snapshot series directly.
- **Alerts (4B)** are computed by `detect_alerts(prev, curr)` comparing the two
  most recent snapshots. Because comparison is always consecutive, a one-off
  regression raises exactly one `Alert` and does not re-fire on later captures —
  natural de-duplication without extra state.

Snapshots are captured at natural moments — after each ingest job, on a manual
`POST …/snapshot`, and by the existing scheduler tick (`capture_stale`, throttled
to ≥12h per repo) — so the series advances with or without activity, without a
dedicated always-on sweep.

Alerts surface in the **in-app notification center** (a topbar bell fed by a
cross-repo `GET /alerts`) and inline on the repository page. Slack delivery of
alerts is intentionally deferred: it adds outbound noise and another opt-in
surface, and the in-app feed covers the core need.

Thresholds live as module constants (`HEALTH_DROP`, …) — tunable in one place,
unit-tested as a pure function.

## Consequences

- One table, one capture path, two features — no duplicated history logic.
- No new dependency and no new always-on process; capture rides the existing
  ingest worker and digest scheduler ($0, single-instance posture preserved).
- The trend chart is a single-series time series (dataviz: no legend, 2px line,
  recessive axes) reusing the app's primary hue — no palette validation needed.
- Trade-off: snapshot cadence is coarse (event-driven + ≥12h periodic), so trend
  lines are not minute-resolution. Fine for a knowledge-health signal; a finer
  cadence is a later change to one throttle constant.
- Alerts are advisory and acknowledgeable — consistent with the human-in-the-loop
  posture; nothing is auto-actioned.
