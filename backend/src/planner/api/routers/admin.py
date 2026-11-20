"""Hiérarchie administrative : Région -> District / Arrondissement -> Commune -> Fokontany."""
from typing import Annotated

from fastapi import APIRouter, Path, Query

from planner.api.deps import ServiceDep
from planner.api.schemas import AdminUnit, EndpointInfo, FokontanyItem, Region, SearchResult

router = APIRouter(tags=["référentiel administratif"])
PCode = Annotated[str, Path(pattern=r"^MG\d{2,11}$", examples=["MG11"])]


@router.get("/regions", response_model=list[Region], summary="Régions (Analamanga en premier)")
def regions(service: ServiceDep) -> list[dict]:
    return service.regions()


@router.get("/regions/{adm1}/districts", response_model=list[AdminUnit], summary="Districts / arrondissements")
def districts(adm1: PCode, service: ServiceDep) -> list[dict]:
    return service.districts(adm1)


@router.get("/districts/{adm2}/communes", response_model=list[AdminUnit], summary="Communes d'un district")
def communes(adm2: PCode, service: ServiceDep) -> list[dict]:
    return service.communes(adm2)


@router.get("/communes/{adm3}/fokontany", response_model=list[FokontanyItem],
            summary="Fokontany d'une commune, avec état de desserte")
def fokontany_of(adm3: PCode, service: ServiceDep) -> list[dict]:
    return service.fokontany_of(adm3)


@router.get("/fokontany/{adm4}", response_model=EndpointInfo,
            summary="Fiche d'un fokontany : hiérarchie, points du réseau, lignes, repli")
def fokontany(adm4: PCode, service: ServiceDep) -> dict:
    return service.fokontany_detail(adm4)


@router.get("/search", response_model=list[SearchResult], summary="Recherche par nom, pcode ou nom d'arrêt")
def search(service: ServiceDep,
           q: Annotated[str, Query(min_length=1, max_length=80, examples=["Analakely"])],
           limit: Annotated[int, Query(ge=1, le=50)] = 20) -> list[dict]:
    return service.search(q, limit)
