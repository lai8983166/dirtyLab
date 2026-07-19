"""Top-level API router aggregating feature routers."""
from __future__ import annotations

from fastapi import APIRouter

from app.api import (
    analyses,
    artifacts,
    connections,
    evaluations,
    experiments,
    providers,
    scoring,
    sync,
)


router = APIRouter()
router.include_router(connections.router, prefix="/connections", tags=["connections"])
router.include_router(providers.router, prefix="/providers", tags=["providers"])
router.include_router(experiments.router, prefix="/experiments", tags=["experiments"])
router.include_router(sync.router, prefix="/sync", tags=["sync"])
router.include_router(evaluations.router, prefix="/evaluations", tags=["evaluations"])
router.include_router(analyses.router, prefix="/analyses", tags=["analyses"])
router.include_router(artifacts.router, prefix="/artifacts", tags=["artifacts"])
router.include_router(scoring.router, prefix="/scoring", tags=["scoring"])
