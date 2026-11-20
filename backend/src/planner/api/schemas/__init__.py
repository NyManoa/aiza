"""Contrats d'API (Pydantic v2) — source de vérité du schéma OpenAPI."""
from planner.api.schemas.admin import AdminUnit, FokontanyItem, Region, SearchResult, ServedSummary
from planner.api.schemas.itinerary import EndpointInfo, Itinerary, RouteResponse
from planner.api.schemas.network import LinesResponse, Meta, Place

__all__ = ["AdminUnit", "EndpointInfo", "FokontanyItem", "Itinerary", "LinesResponse", "Meta", "Place",
           "Region", "RouteResponse", "SearchResult", "ServedSummary"]
