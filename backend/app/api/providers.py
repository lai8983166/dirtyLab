"""Provider (multimodal API) configuration."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_config
from app.db.base import get_db
from app.schemas import ProviderIn, ProviderOut
from app.schemas.repositories import provider_to_schema
from app.services import connection_repo, secrets

router = APIRouter()


@router.get("", response_model=ProviderOut | None)
def get_provider(db: Session = Depends(get_db)) -> ProviderOut | None:
    obj = connection_repo.get_active_provider(db)
    return provider_to_schema(obj) if obj else None


@router.put("", response_model=ProviderOut)
def save_provider(payload: ProviderIn, db: Session = Depends(get_db)) -> ProviderOut:
    cfg = get_config()
    ref = "provider_api_key"
    secrets.write_secret(cfg, ref, payload.api_key)
    obj = connection_repo.upsert_provider(
        db,
        kind=payload.kind,
        base_url=payload.base_url,
        model=payload.model,
        api_key_ref=ref,
    )
    return provider_to_schema(obj)
