"""Repositories wrap SQLAlchemy sessions with domain operations.

Each repository is small and focused; services compose them. We avoid
returning ORM objects across boundaries - everything is converted to a Pydantic
schema (see ``app/schemas``) before leaving the service layer.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models import Connection, Provider


def get_active_connection(db: Session) -> Connection | None:
    return db.scalar(select(Connection).where(Connection.is_active.is_(True)))


def get_connection_by_id(db: Session, connection_id: str) -> Connection:
    obj = db.get(Connection, connection_id)
    if obj is None:
        raise NotFoundError("Connection not found", details={"id": connection_id})
    return obj


def upsert_connection(
    db: Session,
    *,
    host: str,
    port: int,
    username: str,
    private_key_ref: str,
    remote_root: str,
    comfyui_input_path: str = "input",
    comfyui_output_prefix: str = "ComfyUI_",
) -> Connection:
    """There is at most one active connection. Save replaces it."""
    existing = get_active_connection(db)
    if existing is None:
        obj = Connection(
            host=host,
            port=port,
            username=username,
            private_key_ref=private_key_ref,
            remote_root=remote_root.rstrip("/"),
            comfyui_input_path=comfyui_input_path,
            comfyui_output_prefix=comfyui_output_prefix,
            is_active=True,
        )
        db.add(obj)
    else:
        existing.host = host
        existing.port = port
        existing.username = username
        existing.private_key_ref = private_key_ref
        existing.remote_root = remote_root.rstrip("/")
        existing.comfyui_input_path = comfyui_input_path
        existing.comfyui_output_prefix = comfyui_output_prefix
        obj = existing
    db.commit()
    db.refresh(obj)
    return obj


def record_connection_test(
    db: Session,
    connection: Connection,
    *,
    status: str,
    detail: str | None,
) -> None:
    connection.last_test_status = status
    connection.last_test_at = datetime.utcnow()
    connection.last_test_detail = detail
    db.commit()


def get_active_provider(db: Session) -> Provider | None:
    return db.scalar(select(Provider).where(Provider.is_active.is_(True)))


def get_provider_by_id(db: Session, provider_id: str) -> Provider:
    obj = db.get(Provider, provider_id)
    if obj is None:
        raise NotFoundError("Provider not found", details={"id": provider_id})
    return obj


def upsert_provider(
    db: Session,
    *,
    kind: str,
    base_url: str,
    model: str,
    api_key_ref: str,
    label: str = "default",
) -> Provider:
    existing = get_active_provider(db)
    if existing is None:
        obj = Provider(
            kind=kind,
            label=label,
            base_url=base_url,
            model=model,
            api_key_ref=api_key_ref,
            is_active=True,
        )
        db.add(obj)
    else:
        existing.kind = kind
        existing.base_url = base_url
        existing.model = model
        existing.api_key_ref = api_key_ref
        existing.label = label
        obj = existing
    db.commit()
    db.refresh(obj)
    return obj


def to_dict(obj: Any) -> dict[str, Any]:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def assert_unique_active(value: bool, total_active: int) -> None:
    if value and total_active > 1:
        raise ConflictError("Only one active row is allowed")
