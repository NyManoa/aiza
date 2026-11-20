"""Injection de dépendances : le service est créé une fois et partagé entre requêtes.

Normalement créé au démarrage (lifespan). Certains hébergeurs serverless (Vercel) n'exécutent pas le lifespan :
le service est alors créé paresseusement à la première requête (thread-safe).
"""
from __future__ import annotations

import threading
from typing import Annotated

from fastapi import Depends, Request

from planner.engine import TransportService
from planner.settings import get_settings

_lock = threading.Lock()


def get_service(request: Request) -> TransportService:
    state = request.app.state
    svc = getattr(state, "service", None)
    if svc is None:
        with _lock:
            svc = getattr(state, "service", None)
            if svc is None:
                svc = TransportService.from_settings(get_settings())
                svc.warm_up()
                state.service = svc
    return svc


ServiceDep = Annotated[TransportService, Depends(get_service)]
