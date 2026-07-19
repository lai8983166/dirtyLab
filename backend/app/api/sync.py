"""Sync endpoints - placeholder, real implementation in section 4."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db.base import get_db
from app.services import connection_repo, experiment_repo
from app.services import sync as sync_service


router = APIRouter()


@router.post("/experiments/{experiment_id}", response_model=sync_service.SyncResultOut)
def sync_experiment(
    experiment_id: str,
    db: Session = Depends(get_db),
) -> sync_service.SyncResultOut:
    experiment = experiment_repo.get_experiment(db, experiment_id)
    connection = connection_repo.get_active_connection(db)
    if connection is None:
        raise NotFoundError(
            "No AutoDL connection is configured. Open AutoDL Connection first.",
            details={"experiment_id": experiment_id},
        )
    return sync_service.run_sync(db, experiment, connection)
