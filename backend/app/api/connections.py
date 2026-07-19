"""Connection settings + connection test endpoint.

See spec: autodl-comfyui-sync - Configure one AutoDL connection / Test the AutoDL connection.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_config
from app.db.base import get_db
from app.schemas import ConnectionIn, ConnectionOut, ConnectionTestResult
from app.schemas.repositories import connection_to_schema
from app.services import connection_repo, secrets
from app.services.connection_test import check_connection


router = APIRouter()


@router.get("", response_model=ConnectionOut | None)
def get_connection(db: Session = Depends(get_db)) -> ConnectionOut | None:
    obj = connection_repo.get_active_connection(db)
    return connection_to_schema(obj) if obj else None


@router.put("", response_model=ConnectionOut)
def save_connection(payload: ConnectionIn, db: Session = Depends(get_db)) -> ConnectionOut:
    cfg = get_config()
    # Store key material locally; db only holds the reference.
    ref = "autodl_private_key"
    secrets.write_secret(cfg, ref, payload.private_key)
    obj = connection_repo.upsert_connection(
        db,
        host=payload.host,
        port=payload.port,
        username=payload.username,
        private_key_ref=ref,
        remote_root=payload.remote_root,
        comfyui_input_path=payload.comfyui_input_path,
        comfyui_output_prefix=payload.comfyui_output_prefix,
    )
    return connection_to_schema(obj)


@router.post("/test", response_model=ConnectionTestResult)
def run_connection_test(db: Session = Depends(get_db)) -> ConnectionTestResult:
    cfg = get_config()
    obj = connection_repo.get_active_connection(db)
    if obj is None:
        return ConnectionTestResult(
            ok=False,
            stage="ssh_access",
            detail="No connection is configured. Open AutoDL Connection to set it up.",
        )
    result = check_connection(cfg, obj)
    connection_repo.record_connection_test(
        db,
        obj,
        status="ok" if result.ok else "failed",
        detail=result.detail,
    )
    return result
