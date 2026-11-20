"""Résolution d'une extrémité (fokontany) en points d'accès au réseau, avec distance de marche.

Modes d'accès (du plus sûr au plus approximatif) :
  direct        lieu du réseau rattaché au fokontany (marche ≈ 0)
  commune       lieu rattaché seulement à la commune (marche estimée jusqu'à son point)
  passage       ligne qui traverse probablement le fokontany entre deux arrêts (déclaré ou estimé)
  proche_a_pied arrêt d'un fokontany voisin à moins de NEARBY_ACCESS_KM (toujours proposé : accès le plus court)
  repli_a_pied  fokontany sans desserte : fokontany desservis les plus proches (avec alerte au-delà du seuil)
Pour chaque lieu, l'accès retenu est celui de moindre coût explicite : W_WALK_KM × marche + W_CONFIDENCE × (1 − confiance).
"""
from __future__ import annotations

from planner import rules
from planner.core.geo import haversine_km
from planner.engine.repository import NetworkRepository


def access_cost(a: dict) -> float:
    return rules.W_WALK_KM * a["walk_km"] + rules.W_CONFIDENCE * (1 - a["confidence"])


class EndpointResolver:
    def __init__(self, repo: NetworkRepository) -> None:
        self.repo = repo

    def _rings(self, adm4: str, max_ring: int) -> dict[str, int]:
        found: dict[str, int] = {}
        frontier, seen = [adm4], {adm4}
        for ring in range(1, max_ring + 1):
            nxt = []
            for c in frontier:
                for n in self.repo.neighbors.get(c, []):
                    if n not in seen:
                        seen.add(n)
                        nxt.append(n)
                        found[n] = ring
            frontier = nxt
        return found

    def nearest_served(self, adm4: str, k: int = rules.FALLBACK_ALTERNATIVES) -> list[dict]:
        """Fokontany desservis directement les plus proches : anneaux de voisinage administratif, puis distance."""
        repo = self.repo
        f = repo.require_fokontany(adm4)
        found = {c: r for c, r in self._rings(adm4, rules.FALLBACK_MAX_RINGS).items() if c in repo.direct_served}
        res = []
        if f["lat"] is not None:
            for c in (found.keys() if found else repo.direct_served):
                g = repo.fokontany.get(c)
                if g and g["lat"] is not None:
                    res.append({"adm4_pcode": c, "ring": found.get(c),
                                "distance_km": round(haversine_km(f["lat"], f["lon"], g["lat"], g["lon"]), 2)})
        res.sort(key=lambda x: (x["ring"] if x["ring"] is not None else 99, x["distance_km"], x["adm4_pcode"]))
        out = []
        for r in res[:k]:
            g = repo.fokontany[r["adm4_pcode"]]
            out.append({**r, "adm4_name": g["adm4_name"], "adm3_name": g["adm3_name"],
                        "within_limit": r["distance_km"] <= rules.FALLBACK_MAX_KM,
                        "relation": f"voisin de rang {r['ring']}" if r["ring"] else "plus proche à vol d'oiseau"})
        return out

    def _nearest_places(self, adm4: str, k: int | None) -> list[tuple[float, str]]:
        """Lieux réels du réseau triés par distance au centroïde du fokontany."""
        here = self.repo.fokontany_coord(adm4)
        if not here:
            return []
        out = []
        for pid, p in self.repo.places.items():
            if p.get("virtual") or p.get("lat") is None or pid not in self.repo.place_positions:
                continue
            out.append((round(haversine_km(*here, p["lat"], p["lon"]), 2), pid))
        out.sort()
        return out[:k] if k else out

    def extended(self, adm4: str, base: dict[str, dict]) -> dict[str, dict]:
        """Palier 2 : accès de base + les arrêts les plus proches, quelle que soit la distance (marche comptée)."""
        access = dict(base)
        for d, pid in self._nearest_places(adm4, rules.EXTENDED_ACCESS_K):
            p = self.repo.places[pid]
            self._offer(access, {"place": pid, "mode": "repli_a_pied", "status": p["match_status"],
                                 "confidence": p["confidence"], "walk_km": d,
                                 "via_fokontany": self._via(pid, "arrêt le plus proche")})
        return access

    def approach(self, adm4: str, base: dict[str, dict]) -> dict[str, dict]:
        """Palier 3 (arrivée) : n'importe quel point du réseau, puis marche jusqu'au fokontany d'arrivée."""
        access = dict(base)
        for d, pid in self._nearest_places(adm4, None):
            p = self.repo.places[pid]
            self._offer(access, {"place": pid, "mode": "approche_a_pied", "status": p["match_status"],
                                 "confidence": p["confidence"], "walk_km": d,
                                 "via_fokontany": self._via(pid, "approche à pied")})
        return access

    def _via(self, pid: str, relation: str) -> dict | None:
        codes = [c for c in (self.repo.places[pid].get("fokontany") or "").split(";") if c]
        if not codes:
            return {"adm4_pcode": "", "adm4_name": self.repo.places[pid]["name"], "relation": relation}
        f = self.repo.fokontany[codes[0]]
        return {"adm4_pcode": codes[0], "adm4_name": f["adm4_name"], "relation": relation}

    def _offer(self, access: dict[str, dict], a: dict) -> None:
        cur = access.get(a["place"])
        if cur is None or (access_cost(a), a["mode"]) < (access_cost(cur), cur["mode"]):
            access[a["place"]] = a

    def resolve(self, adm4: str) -> dict:
        """Retourne {fokontany, served, access: {place_id: accès}, fallback, warnings}."""
        repo = self.repo
        repo.require_fokontany(adm4)
        here = repo.fokontany_coord(adm4)
        info = {"fokontany": repo.admin_label(adm4), "served": repo.served_summary(adm4), "access": {},
                "fallback": [], "warnings": []}
        access: dict[str, dict] = info["access"]

        for e in repo.served.get(adm4, []):
            walk = 0.0
            if e["mode"] == "commune" and here and (pc := repo.place_coord(e["place"])):
                walk = round(haversine_km(*here, *pc), 2)
            self._offer(access, {"place": e["place"], "mode": e["mode"], "status": e["status"],
                                 "confidence": e["confidence"], "walk_km": walk, "via_fokontany": None})

        # Arrêts des fokontany voisins à distance de marche : souvent un accès plus court qu'une correspondance.
        if here:
            for code, ring in sorted(self._rings(adm4, rules.NEARBY_ACCESS_RINGS).items()):
                g = repo.fokontany_coord(code)
                if code not in repo.direct_served or not g:
                    continue
                d = round(haversine_km(*here, *g), 2)
                if d > rules.NEARBY_ACCESS_KM:
                    continue
                for e in repo.served[code]:
                    if e["mode"] == "direct":
                        self._offer(access, {
                            "place": e["place"], "mode": "proche_a_pied", "status": e["status"],
                            "confidence": e["confidence"], "walk_km": d,
                            "via_fokontany": {"adm4_pcode": code, "adm4_name": repo.fokontany[code]["adm4_name"],
                                              "relation": f"voisin de rang {ring}"}})

        if adm4 in repo.direct_served:
            return info
        fb = self.nearest_served(adm4)
        info["fallback"] = fb
        lst = repo.served.get(adm4, [])
        if any(e["mode"] == "commune" for e in lst):
            info["warnings"].append("Desserte uniquement au niveau de la commune (rattachement approximatif).")
        elif any(e["mode"] == "passage" for e in lst):
            info["warnings"].append("Aucun arrêt publié dans ce fokontany : des lignes le traversent probablement "
                                    "(accès « en passage » à confirmer).")
        else:
            info["warnings"].append("Aucune ligne ne dessert directement ce fokontany (zone sans ligne directe).")
        if fb and not fb[0]["within_limit"]:
            info["warnings"].append(
                f"Limite de desserte : le point desservi le plus proche ({fb[0]['adm4_name']}) est à "
                f"{fb[0]['distance_km']} km, au-delà du seuil de marche de {rules.FALLBACK_MAX_KM} km.")
        for alt in fb:
            for e in repo.served.get(alt["adm4_pcode"], []):
                if e["mode"] == "direct":
                    self._offer(access, {
                        "place": e["place"], "mode": "repli_a_pied", "status": e["status"],
                        "confidence": e["confidence"], "walk_km": alt["distance_km"],
                        "via_fokontany": {"adm4_pcode": alt["adm4_pcode"], "adm4_name": alt["adm4_name"],
                                          "relation": alt["relation"]}})
        return info
