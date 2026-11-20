"""Point d'entrée Vercel (fonction Python serverless) : expose l'application FastAPI du backend.

Toutes les requêtes /api/* y sont réécrites par vercel.json ; le chemin d'origine (/api/v1/...) est conservé.
Les données lues sont backend/data/processed/ (générées par `make pipeline`, incluses via `includeFiles`).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from planner.api.app import app  # noqa: E402, F401 — variable ASGI détectée par Vercel
