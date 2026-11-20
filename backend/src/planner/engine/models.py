"""Objets du domaine."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Position:
    """Position le long d'un service : arrêt publié (real) ou fokontany traversé (virtuel, « passage »)."""

    places: tuple[str, ...]
    real: bool
    km: float           # distance cumulée depuis le début du service (vol d'oiseau)
    unknown: int        # nombre cumulé de tronçons de longueur inconnue depuis le début


@dataclass(frozen=True, slots=True)
class Ride:
    """Une course : monter en position i et descendre en position j d'un même service."""

    service: int        # index dans NetworkRepository.services
    i: int              # position de montée (positions étendues)
    j: int              # position de descente
    src: str            # place_id de montée
    dst: str            # place_id de descente
    reverse: bool       # sens retour supposé (variante non circulaire)
    wrap: bool          # passage par le terminus d'une boucle
    km: float           # distance parcourue (vol d'oiseau)
    km_unknown: int     # tronçons de longueur inconnue parcourus
    n_stops: int        # arrêts publiés intermédiaires

    def cost_key(self) -> tuple[bool, bool, float]:
        return (self.reverse, self.wrap, round(self.km, 3))
