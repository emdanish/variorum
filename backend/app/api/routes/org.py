from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import User
from app.schemas import ExpertDirectory, Portfolio
from app.services import experts as experts_svc
from app.services import portfolio as portfolio_svc

router = APIRouter(tags=["org"])


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
