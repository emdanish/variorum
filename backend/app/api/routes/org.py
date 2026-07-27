from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import Repository, User
from app.schemas import AlertResponse, ExpertDirectory, Portfolio
from app.services import experts as experts_svc
from app.services import monitoring as monitoring_svc
from app.services import portfolio as portfolio_svc

router = APIRouter(tags=["org"])


@router.get("/alerts", response_model=list[AlertResponse])
def alerts(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AlertResponse]:
    """Unacknowledged alerts across the user's repositories — the notification feed."""
    rows = monitoring_svc.list_alerts_for_user(db, user.id)
    names = {
        r.id: r.full_name
        for r in db.query(Repository).filter(
            Repository.id.in_({a.repository_id for a in rows})
        )
    }
    return [
        AlertResponse(
            id=a.id,
            repository_id=a.repository_id,
            kind=a.kind,
            severity=a.severity,
            title=a.title,
            detail=a.detail,
            created_at=a.created_at,
            acknowledged_at=a.acknowledged_at,
            repo_full_name=names.get(a.repository_id),
        )
        for a in rows
    ]


@router.get("/portfolio", response_model=Portfolio)
def portfolio(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Portfolio:
    """Org-wide knowledge-health view across all connected repositories."""
    return Portfolio(**portfolio_svc.build_portfolio(db, user.id))


@router.get("/experts", response_model=ExpertDirectory)
def experts(
    q: str | None = Query(default=None, max_length=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExpertDirectory:
    """Expertise directory: who knows what across the connected repositories."""
    return ExpertDirectory(**experts_svc.build_experts(db, user.id, q=q))
