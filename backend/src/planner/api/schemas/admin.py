from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

MatchStatus = Literal["exact_fokontany", "sous_chaine_fokontany", "commune", "repere_ou_variante",
                      "non_resolu", "non_desservi", "passage_declare", "passage_estime"]
Coverage = Literal["direct", "commune", "passage", "aucune"]


class ServedSummary(BaseModel):
    n_places: int = Field(description="Lieux du réseau desservant le fokontany")
    n_direct: int = Field(description="Dont rattachés directement au fokontany")
    n_passage: int = Field(0, description="Lignes traversant probablement le fokontany (accès « en passage »)")
    n_lines: int
    best_status: MatchStatus
    best_confidence: float
    coverage: Coverage


class AdminUnit(BaseModel):
    pcode: str
    name: str
    area_sqkm: float | None = None
    n_children: int


class Region(AdminUnit):
    old_province: str | None = None


class FokontanyItem(BaseModel):
    pcode: str
    name: str
    area_sqkm: float | None = None
    served: ServedSummary


class FokontanyLabel(BaseModel):
    adm4_pcode: str
    adm4_name: str
    adm3_pcode: str
    adm3_name: str
    adm2_pcode: str
    adm2_name: str
    adm1_pcode: str
    adm1_name: str
    area_sqkm: float | None = None
    lat: float | None = None
    lon: float | None = None


class SearchResult(FokontanyLabel):
    match: Literal["pcode", "nom", "arret"]
    via_place: str | None = None
    served: ServedSummary
