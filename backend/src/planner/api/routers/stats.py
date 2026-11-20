from typing import Any

from fastapi import APIRouter

from planner.api.deps import ServiceDep

router = APIRouter(tags=["analyse"])


@router.get("/stats", summary="Statistiques descriptives et couverture (produites par le pipeline)")
def stats(service: ServiceDep) -> dict[str, Any]:
    return service.stats()
