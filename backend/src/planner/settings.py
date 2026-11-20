"""Paramètres d'infrastructure (chemins, CORS, serveur), surchargeables par variables d'environnement.

Préfixe : PLANNER_  (ex. PLANNER_DATA_DIR=/srv/data, PLANNER_CORS_ORIGINS='["https://tana.example"]').
Les règles métier (confiances, poids du score…) sont dans `planner.rules`, pas ici.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PLANNER_", env_file=".env", extra="ignore")

    app_name: str = "Planificateur de transport — Antananarivo"
    api_prefix: str = "/api/v1"
    environment: str = "development"
    data_dir: Path = BACKEND_ROOT / "data"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])
    log_level: str = "info"

    # --- chemins dérivés ------------------------------------------------------
    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def reference_dir(self) -> Path:
        return self.data_dir / "reference"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def admin_xlsx(self) -> Path:
        return self.raw_dir / "mdg_admin_boundaries.xlsx"

    @property
    def bus_txt(self) -> Path:
        return self.raw_dir / "liste_bus_antananarivo.txt"

    @property
    def manual_places_csv(self) -> Path:
        return self.reference_dir / "manual_places.csv"

    @property
    def token_aliases_csv(self) -> Path:
        return self.reference_dir / "token_aliases.csv"

    @property
    def tables_dir(self) -> Path:
        return self.processed_dir / "tables"

    @property
    def graph_dir(self) -> Path:
        return self.processed_dir / "graph"

    @property
    def analysis_dir(self) -> Path:
        return self.processed_dir / "analysis"

    @property
    def network_json(self) -> Path:
        return self.graph_dir / "network.json"

    @property
    def stats_json(self) -> Path:
        return self.analysis_dir / "stats.json"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
