from fastapi import APIRouter

from planner.api.deps import ServiceDep
from planner.api.schemas import LinesResponse, Place

router = APIRouter(prefix="/network", tags=["réseau"])


@router.get("/lines", response_model=LinesResponse, summary="Lignes, variantes et liaisons Primus -> Terminus")
def lines(service: ServiceDep) -> dict:
    return service.lines()


@router.get("/places", response_model=list[Place], summary="Lieux du réseau et rattachement au référentiel")
def places(service: ServiceDep) -> list[dict]:
    return service.places()
