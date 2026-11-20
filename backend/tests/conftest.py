"""Fixtures partagées. Pré-requis : `python -m planner.pipeline` a produit data/processed/."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from planner.api.app import create_app
from planner.engine import TransportService
from planner.settings import get_settings


@pytest.fixture(scope="session")
def settings():
    s = get_settings()
    if not s.network_json.exists():
        pytest.exit("data/processed/ absent : lancer `python -m planner.pipeline` avant les tests.", 2)
    return s


@pytest.fixture(scope="session")
def service(settings) -> TransportService:
    return TransportService.from_settings(settings)


@pytest.fixture(scope="session")
def client(settings, service):
    with TestClient(create_app(settings, service)) as c:
        yield c


@pytest.fixture(scope="session")
def code(service):
    def _code(name: str, commune: str) -> str:
        return next(c for c, f in service.repo.fokontany.items()
                    if f["adm4_name"] == name and f["adm3_name"] == commune)
    return _code


@pytest.fixture(scope="session")
def analakely_itaosy(service, code):
    return service.plan(code("Antanimalalaka Analakely", "1er Arrondissement"), code("Itaosy", "Itaosy"))
