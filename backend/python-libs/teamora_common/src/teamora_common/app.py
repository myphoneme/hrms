"""App factory and runner shared by every Teamora FastAPI service."""

from __future__ import annotations

import logging
import sys
import threading
from collections.abc import Callable, Iterable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse

from .config import ConfigError, ServiceConfig, ServiceDefinition, load_service_config
from .db import create_pool
from .env_file import apply_env_file_arg
from .errors import install_error_handlers

logger = logging.getLogger("teamora")

API_PREFIX = "/api/v1"
API_DOCS_PATH = "/api/docs"


def _health_router() -> APIRouter:
    router = APIRouter(tags=["Health"])

    @router.get("/health", summary="Liveness: the process is up (Coolify health check, SOP §8.3)")
    def live(request: Request) -> dict[str, Any]:
        config: ServiceConfig = request.app.state.config
        return {"status": "ok", "service": config.service_name, "appEnv": config.app_env}

    @router.get("/health/ready", summary="Readiness: the service can query its database as its own role")
    def ready(request: Request) -> Any:
        name = request.app.state.config.service_name
        try:
            with request.app.state.pool.connection() as conn:
                conn.execute("SELECT 1")
        except Exception:  # noqa: BLE001
            # No error detail in the response: it could reveal hosts or usernames.
            return JSONResponse({"status": "error", "service": name, "checks": {"database": "down"}}, status_code=503)
        return {"status": "ok", "service": name, "checks": {"database": "up"}}

    return router


#: A background worker: runs for the app's lifetime in its own thread and returns once ``stop`` is set.
Worker = Callable[[FastAPI, threading.Event], None]


def create_app(config: ServiceConfig, routers: Iterable[APIRouter], pool: Any = None, workers: Iterable[Worker] = ()) -> FastAPI:
    """Builds a service app: health endpoints at the root, business routers under /api/v1, the standard
    error format, the database pool (opened on startup, closed on shutdown) and any background workers
    (e.g. a scheduled check), each started in its own thread after the pool opens and stopped before it closes.

    ``pool`` replaces the real connection pool in tests. The interactive API page (Swagger UI) is served
    only when APP_ENV is local or test, never on staging or production.
    """
    owns_pool = pool is None
    pool = create_pool(config) if owns_pool else pool
    workers = list(workers)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if owns_pool:
            pool.open(wait=False)
        stop = threading.Event()
        threads = [
            threading.Thread(target=worker, args=(app, stop), name=getattr(worker, "__name__", "worker"), daemon=True)
            for worker in workers
        ]
        for thread in threads:
            thread.start()
        try:
            yield
        finally:
            stop.set()
            for thread in threads:
                thread.join(timeout=10)
            if owns_pool:
                pool.close()

    docs = config.app_env in ("local", "test")
    app = FastAPI(
        title=f"Teamora {config.service_name}",
        version="0.1.0",
        description=(
            "Local/test only. Click **Authorize** and paste a token from `python dev/make_token.py` "
            "(backend/dev/README.md). Errors come back as `{ reason, message, details? }`."
        ),
        docs_url=API_DOCS_PATH if docs else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if docs else None,
        swagger_ui_parameters={"persistAuthorization": True},
        lifespan=lifespan,
    )
    app.state.config = config
    app.state.pool = pool
    install_error_handlers(app)
    app.include_router(_health_router())
    for router in routers:
        app.include_router(router, prefix=API_PREFIX)
    return app


def run_service(definition: ServiceDefinition, build_app) -> None:
    """Entry point for ``python -m <service> [--env-file PATH]``.

    Loads and validates configuration (exits listing every problem), then serves the app and logs
    APP_ENV and the database target at startup (Charter, Database rules 7).
    """
    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    apply_env_file_arg(sys.argv[1:])
    try:
        config = load_service_config(definition)
        app = build_app(config)
    except ConfigError as exc:
        logger.error(str(exc))
        sys.exit(1)

    db = config.db
    logger.info(
        "%s listening on :%s | APP_ENV=%s | DB=%s@%s:%s/%s",
        config.service_name,
        config.port,
        config.app_env,
        db.user,
        db.host,
        db.port,
        db.database,
    )
    if config.app_env in ("local", "test"):
        logger.info("API docs (local/test only): http://localhost:%s%s", config.port, API_DOCS_PATH)
    uvicorn.run(app, host="0.0.0.0", port=config.port, log_config=None)
