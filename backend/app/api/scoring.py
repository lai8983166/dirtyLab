"""Scoring template endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas import TemplateIn, TemplateOut
from app.schemas.repositories import template_to_schema
from app.services import template_repo

router = APIRouter()


@router.get("", response_model=TemplateOut)
def get_active_template(db: Session = Depends(get_db)) -> TemplateOut:
    return template_to_schema(template_repo.get_active_template(db))


@router.get("/all", response_model=list[TemplateOut])
def list_templates(db: Session = Depends(get_db)) -> list[TemplateOut]:
    return [template_to_schema(t) for t in template_repo.list_templates(db)]


@router.post("", response_model=TemplateOut)
def new_template(payload: TemplateIn, db: Session = Depends(get_db)) -> TemplateOut:
    return template_to_schema(
        template_repo.new_template_version(
            db,
            dimensions=[d.model_dump() for d in payload.dimensions],
            tags=[t.model_dump() for t in payload.tags],
        )
    )
