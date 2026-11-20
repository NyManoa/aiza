from __future__ import annotations

from pydantic import BaseModel, Field


class Meta(BaseModel):
    version: str
    network: dict
    n_regions: int
    n_fokontany: int
    n_fokontany_served: int
    default_region: str
    max_transfers: int
    max_walk_km: float
    max_rings: int
    weights: dict[str, float]


class Line(BaseModel):
    line_id: str
    line_code: str
    zone: str
    group: str | None = None
    note: str | None = None
    n_variants: int


class CorridorItem(BaseModel):
    adm4_pcode: str
    name: str
    source: str


class Service(BaseModel):
    id: str
    line_id: str
    line_code: str
    zone: str
    label: str
    sector: str | None = None
    color: str | None = None
    note: str | None = None
    loop: bool
    stops: list[list[str]]
    stops_named: list[list[str]]
    stops_known: bool
    via_mention: str | None = None
    raw: str
    seg_km: list[float | None] = Field(default_factory=list)
    corridor_named: list[list[CorridorItem]] = Field(default_factory=list)
    length_km: float = 0.0


class LinesResponse(BaseModel):
    lines: list[Line]
    services: list[Service]


class Place(BaseModel):
    place_id: str
    name: str
    match_status: str
    match_rule: str
    match_level: str
    confidence: float
    match_detail: str
    fokontany: str | None = None
    communes: str | None = None
    lat: float | None = None
    lon: float | None = None
    coord_quality: str = "inconnue"
    in_degree: int
    out_degree: int
    n_lines: int
    n_services: int
    n_passages: int
    zones: str
    roles: str
