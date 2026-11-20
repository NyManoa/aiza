from fastapi import APIRouter

from planner.api.deps import ServiceDep
from planner.api.schemas import Meta

router = APIRouter(tags=["système"])


@router.get("/health", summary="Sonde de disponibilité")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/meta", response_model=Meta, summary="Chiffres clés et paramètres de classement")
def meta(service: ServiceDep) -> dict:
    return service.meta()
