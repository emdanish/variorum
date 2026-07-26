from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models import Repository

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.get("")
def list_repositories(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(select(Repository).order_by(Repository.full_name)).scalars().all()
    return [
        {
            "id": repo.id,
            "full_name": repo.full_name,
            "default_branch": repo.default_branch,
            "private": repo.private,
            "indexing_status": repo.indexing_status.value,
            "last_indexed_at": repo.last_indexed_at.isoformat()
            if repo.last_indexed_at
            else None,
        }
        for repo in rows
    ]
