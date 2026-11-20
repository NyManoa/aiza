"""Fabrique de l'application FastAPI.

  uvicorn planner.api.app:app --reload          (développement)
  uvicorn planner.api.app:app --host 0.0.0.0    (production, voir Dockerfile)
"""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from planner import __version__
from planner.api.routers import admin, health, itineraries, network, stats
from planner.engine import NotFoundError, TransportService
from planner.settings import Settings, get_settings

log = logging.getLogger("planner.api")


def create_app(settings: Settings | None = None, service: TransportService | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        svc = service or TransportService.from_settings(settings)
        svc.warm_up()  # pré-calcul de l'index des courses
        app.state.service = svc
        log.info("Réseau chargé : %s", svc.repo.meta)
        yield

    app = FastAPI(
        title=settings.app_name, version=__version__, lifespan=lifespan,
        description="API du planificateur d'itinéraires d'Antananarivo fondé sur la hiérarchie administrative "
                    "de Madagascar. Règles déterministes, sans IA.",
        docs_url=f"{settings.api_prefix}/docs", redoc_url=f"{settings.api_prefix}/redoc",
        openapi_url=f"{settings.api_prefix}/openapi.json",
    )
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["GET"],
                       allow_headers=["*"])

    @app.exception_handler(NotFoundError)
    async def not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    for r in (health.router, admin.router, itineraries.router, network.router, stats.router):
        app.include_router(r, prefix=settings.api_prefix)
    return app


app = create_app()
