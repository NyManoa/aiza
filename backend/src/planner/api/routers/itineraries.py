from typing import Annotated

from fastapi import APIRouter, Query

from planner import rules
from planner.api.deps import ServiceDep
from planner.api.schemas import RouteResponse

router = APIRouter(tags=["itinéraires"])
Adm4 = Annotated[str, Query(pattern=r"^MG\d{11}$", examples=["MG11118001001"])]


@router.get("/itineraries", response_model=RouteResponse,
            summary="Itinéraires entre deux fokontany (0, 1 ou 2 correspondances)",
            description="Énumération exhaustive bornée, élimination des trajets dominés, "
                        "classement par score explicite (voir `score_breakdown`).")
def itineraries(service: ServiceDep,
                origin: Annotated[str, Query(alias="from", pattern=r"^MG\d{11}$", examples=["MG11118001001"])],
                destination: Annotated[str, Query(alias="to", pattern=r"^MG\d{11}$", examples=["MG11117110001"])],
                max_transfers: Annotated[int, Query(ge=0, le=rules.MAX_TRANSFERS)] = rules.MAX_TRANSFERS) -> dict:
    return service.plan(origin, destination, max_transfers)
