from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from planner.api.schemas.admin import FokontanyLabel, ServedSummary


class PlaceSummary(BaseModel):
    place_id: str
    name: str
    match_status: str
    confidence: float
    fokontany: list[str]
    communes: list[str]
    match_detail: str
    n_lines: int
    virtual: bool = Field(False, description="Fokontany traversé (pas un arrêt publié)")
    lat: float | None = None
    lon: float | None = None
    coord_quality: str = "inconnue"


class ViaFokontany(BaseModel):
    adm4_pcode: str
    adm4_name: str
    relation: str


class Access(BaseModel):
    place: PlaceSummary
    mode: Literal["direct", "commune", "passage", "proche_a_pied", "repli_a_pied", "approche_a_pied"]
    status: str
    confidence: float
    walk_km: float
    via_fokontany: ViaFokontany | None = None


class Fallback(BaseModel):
    adm4_pcode: str
    adm4_name: str
    adm3_name: str
    ring: int | None = None
    distance_km: float
    within_limit: bool
    relation: str


class LineHere(BaseModel):
    service_id: str
    line_code: str
    zone: str
    variant: str
    place: str
    from_: str = Field(alias="from")
    to: str
    passage: bool = False
    other_end_unresolved: bool

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class EndpointInfo(BaseModel):
    fokontany: FokontanyLabel
    served: ServedSummary
    access: list[Access]
    fallback: list[Fallback]
    warnings: list[str]
    lines_here: list[LineHere]


class Leg(BaseModel):
    service_id: str
    line_id: str
    line_code: str
    zone: Literal["urbaine", "suburbaine"]
    variant: str
    sector: str | None = None
    color: str | None = None
    note: str | None = None
    loop: bool
    from_: PlaceSummary = Field(alias="from")
    to: PlaceSummary
    direction: Literal["aller", "retour_suppose"]
    wrap: bool
    n_segments: int | None = None
    stops: list[str]
    passages: list[str] = Field(default_factory=list, description="Fokontany traversés (déclarés ou estimés)")
    km: float = Field(description="Distance parcourue, vol d'oiseau entre arrêts")
    km_unknown: int = Field(0, description="Tronçons de longueur inconnue (valeur par défaut utilisée)")
    headsign: str = Field("", description="Direction (terminus dans le sens de circulation)")
    stops_known: bool
    via_mention: str | None = None
    raw: str

    model_config = {"populate_by_name": True, "serialize_by_alias": True}


class TransferPoint(BaseModel):
    at: PlaceSummary
    to: PlaceSummary
    type: Literal["meme_lieu", "a_pied_meme_fokontany"]
    fokontany: str | None = None
    walk_km: float = 0.0


class ItineraryAccess(BaseModel):
    origin: Access
    destination: Access


class Itinerary(BaseModel):
    id: int
    transfers: int
    score: float
    score_breakdown: dict[str, float]
    legs: list[Leg]
    transfer_points: list[TransferPoint]
    line_ids: list[str]
    zones: list[str]
    confidence_min: float
    statuses: list[str]
    access: ItineraryAccess
    bus_km: float
    walk_km: float
    total_km: float
    direct_km: float | None = None
    detour_ratio: float | None = None
    is_detour: bool
    revisits: int = Field(description="Lieux traversés deux fois (va-et-vient)")
    has_reverse: bool
    has_walk: bool
    has_passage: bool
    signature: str


class RouteResponse(BaseModel):
    origin: EndpointInfo
    destination: EndpointInfo
    itineraries: list[Itinerary]
    counts: dict[str, int] = Field(description="Nombre total d'itinéraires trouvés par nombre de correspondances")
    messages: list[str]
    max_transfers: int
    direct_km: float | None = Field(None, description="Distance à vol d'oiseau entre les deux fokontany")
    pruned: dict[str, int] = Field(default_factory=dict, description="Itinéraires éliminés par règle")
    highlights: dict[str, int | None] = Field(default_factory=dict, description="Identifiants mis en avant")
    search_mode: Literal["normal", "acces_elargi", "approche"] = Field(
        "normal", description="Palier de recherche utilisé (normal, accès élargi, approche à pied)")
