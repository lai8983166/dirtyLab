"""FastAPI application factory + lifespan."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api import routes
from app.core.config import AppConfig, get_config
from app.core.errors import AppError
from app.core.logging import configure_logging, get_logger
from app.db.base import get_engine, init_engine
from app.db.bootstrap import create_schema, ensure_seed_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    config: AppConfig = get_config()
    configure_logging(config)
    log = get_logger("startup")
    log.info("startup", data_dir=str(config.data_dir), db_path=str(config.db_path))
    engine = init_engine(config)
    create_schema(engine)
    from app.db.base import session_scope

    with session_scope() as db:
        ensure_seed_data(db)
    log.info("ready")
    yield
    log.info("shutdown")


def create_app(config: AppConfig | None = None) -> FastAPI:
    if config is not None:
        from app.core.config import set_config

        set_config(config)
    # Make sure config is initialized even when create_app is called without one.
    get_config()

    app = FastAPI(title="dirtyLab", version="0.1.0", lifespan=lifespan)

    cfg = get_config()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.http_status, content=exc.to_payload())

    app.include_router(routes.router, prefix="/api")

    @app.get("/api/health", tags=["system"])
    def health() -> dict:
        from app.schemas import HealthResponse

        cfg = get_config()
        engine = get_engine()
        db_ok = True
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception:
            db_ok = False
        return HealthResponse(
            status="ok" if db_ok else "degraded",
            database=db_ok,
            artifacts_dir=str(cfg.artifacts_dir),
        ).model_dump()

    return app


app = create_app()
