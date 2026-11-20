"""Façade applicative : cas d'usage exposés à l'API (et à la CLI)."""
from __future__ import annotations

import json
from functools import cached_property
from pathlib import Path

from planner import __version__, rules
from planner.core.geo import haversine_km
from planner.engine.endpoints import EndpointResolver
from planner.engine.errors import NotFoundError
from planner.engine.planner import ItineraryPlanner
from planner.engine.repository import NetworkRepository
from planner.engine.search import SearchService
from planner.settings import Settings

SEARCH_MODE_MESSAGE = {
    "acces_elargi": "Aucun trajet avec au plus {k} correspondance(s) depuis les arrêts proches : la recherche a été "
                    "élargie aux arrêts les plus proches de chaque extrémité (marche plus longue, indiquée).",
    "approche": "Aucun trajet avec au plus {k} correspondance(s), même en élargissant l'accès : itinéraire d'approche — "
                "bus (autant de correspondances que nécessaire) jusqu'au point du réseau le plus proche de l'arrivée, "
                "puis fin du trajet à pied.",
}


class TransportService:
    def __init__(self, repo: NetworkRepository, stats_json: Path) -> None:
        self.repo = repo
        self.stats_path = stats_json
        self.search_service = SearchService(repo)
        self.resolver = EndpointResolver(repo)
        self.planner = ItineraryPlanner(repo)

    @classmethod
    def from_settings(cls, s: Settings) -> TransportService:
        if not s.network_json.exists():
            raise FileNotFoundError(f"{s.network_json} introuvable : lancer d'abord `python -m planner.pipeline`.")
        return cls(NetworkRepository(s.network_json, s.tables_dir), s.stats_json)

    def warm_up(self) -> None:
        self.planner.warm_up()

    # ------------------------------------------------------------------ méta
    def meta(self) -> dict:
        r = self.repo
        return {"version": __version__, "network": r.meta, "n_regions": len(r.regions),
                "n_fokontany": len(r.fokontany), "n_fokontany_served": len(r.served),
                "default_region": rules.ANALAMANGA, "max_transfers": rules.MAX_TRANSFERS,
                "max_walk_km": rules.FALLBACK_MAX_KM, "max_rings": rules.FALLBACK_MAX_RINGS,
                "weights": rules.score_weights()}

    # ------------------------------------------------------------------ hiérarchie
    def _unit(self, code: str, row: dict, name_key: str) -> dict:
        return {"pcode": code, "name": row[name_key], "area_sqkm": row["area_sqkm"],
                "n_children": len(self.repo.children.get(code, []))}

    def regions(self) -> list[dict]:
        items = [{**self._unit(c, r, "adm1_name"), "old_province": r.get("old_provin") or None}
                 for c, r in self.repo.regions.items()]
        return sorted(items, key=lambda x: (x["pcode"] != rules.ANALAMANGA, x["name"]))

    def districts(self, adm1: str) -> list[dict]:
        if adm1 not in self.repo.regions:
            raise NotFoundError(f"région inconnue : {adm1}")
        return sorted((self._unit(c, self.repo.districts[c], "adm2_name") for c in self.repo.children[adm1]),
                      key=lambda x: x["name"])

    def communes(self, adm2: str) -> list[dict]:
        if adm2 not in self.repo.districts:
            raise NotFoundError(f"district inconnu : {adm2}")
        return sorted((self._unit(c, self.repo.communes[c], "adm3_name") for c in self.repo.children[adm2]),
                      key=lambda x: x["name"])

    def fokontany_of(self, adm3: str) -> list[dict]:
        if adm3 not in self.repo.communes:
            raise NotFoundError(f"commune inconnue : {adm3}")
        items = [{"pcode": c, "name": self.repo.fokontany[c]["adm4_name"],
                  "area_sqkm": self.repo.fokontany[c]["area_sqkm"], "served": self.repo.served_summary(c)}
                 for c in self.repo.children[adm3]]
        return sorted(items, key=lambda x: x["name"])

    # ------------------------------------------------------------------ extrémités
    def _public_endpoint(self, info: dict) -> dict:
        acc = info["access"]
        out = dict(info)
        out["access"] = [{**a, "place": self.repo.place_summary(a["place"])}
                         for a in sorted(acc.values(), key=lambda a: (-a["confidence"], a["place"]))]
        out["lines_here"] = self.repo.lines_at({p: a["confidence"] for p, a in acc.items()})
        return out

    def fokontany_detail(self, adm4: str) -> dict:
        return self._public_endpoint(self.resolver.resolve(adm4))

    def search(self, q: str, limit: int = 20) -> list[dict]:
        return self.search_service.search(q, limit)

    # ------------------------------------------------------------------ itinéraires
    def plan(self, origin: str, destination: str, max_transfers: int = rules.MAX_TRANSFERS) -> dict:
        o = self.resolver.resolve(origin)
        d = self.resolver.resolve(destination)
        messages: list[str] = []
        itineraries: list[dict] = []
        counts: dict[str, int] = {}
        pruned: dict[str, int] = {}
        highlights: dict[str, int | None] = {}
        direct_km: float | None = None
        search_mode = "normal"
        orig_acc, dest_acc = o["access"], d["access"]
        if origin == destination:
            messages.append("Départ et arrivée identiques : même fokontany.")
        elif not orig_acc or not dest_acc:
            messages.append("Impossible de rejoindre le réseau depuis " + ("le départ." if not orig_acc else "l'arrivée."))
        else:
            common = sorted(set(orig_acc) & set(dest_acc))
            if common:
                messages.append("Départ et arrivée partagent un même point du réseau ("
                                + ", ".join(self.repo.places[c]["name"] for c in common)
                                + ") : trajet à pied possible.")
            fo, fd = self.repo.fokontany_coord(origin), self.repo.fokontany_coord(destination)
            direct_km = haversine_km(*fo, *fd) if fo and fd else None
            k = max(0, min(rules.MAX_TRANSFERS, max_transfers))
            # Recherche par paliers : un itinéraire est toujours proposé (voir rules.EXTENDED_ACCESS_K).
            res = self.planner.plan(orig_acc, dest_acc, k, direct_km)
            if not res["itineraries"]:
                search_mode = "acces_elargi"
                o_ext = self.resolver.extended(origin, orig_acc)
                d_ext = self.resolver.extended(destination, dest_acc)
                res = self.planner.plan(o_ext, d_ext, k, direct_km)
                if not res["itineraries"]:
                    search_mode = "approche"
                    res = self.planner.approach(o_ext, self.resolver.approach(destination, d_ext), direct_km)
                messages.append(SEARCH_MODE_MESSAGE[search_mode].format(k=k))
            itineraries, counts = res["itineraries"], res["counts"]
            pruned, highlights = res["pruned"], res["highlights"]
            if not itineraries:
                messages.append("Aucun itinéraire calculable : le réseau n'est pas accessible depuis ce fokontany.")
        for it in itineraries:
            for k in ("origin", "destination"):
                a = it["access"][k]
                if isinstance(a["place"], str):
                    it["access"][k] = {**a, "place": self.repo.place_summary(a["place"])}
        return {"origin": self._public_endpoint(o), "destination": self._public_endpoint(d),
                "itineraries": itineraries, "counts": counts, "messages": messages,
                "max_transfers": max_transfers, "pruned": pruned, "highlights": highlights,
                "direct_km": round(direct_km, 2) if direct_km is not None else None, "search_mode": search_mode}

    # ------------------------------------------------------------------ réseau & analyse
    def lines(self) -> dict:
        repo = self.repo
        services = []
        for s in repo.services:
            corridor_named = [[{"adm4_pcode": e["adm4"], "name": repo.fokontany[e["adm4"]]["adm4_name"],
                                "source": e["source"]} for e in seg] for seg in s.get("corridor", [])]
            services.append({**s, "stops_named": [[repo.places[p]["name"] for p in pos] for pos in s["stops"]],
                             "corridor_named": corridor_named,
                             "length_km": round(sum(x for x in s.get("seg_km", []) if x is not None), 2)})
        return {"lines": list(repo.lines.values()), "services": services}

    def places(self) -> list[dict]:
        return sorted(self.repo.places.values(), key=lambda p: (-p["n_lines"], p["name"]))

    @cached_property
    def _stats(self) -> dict:
        with open(self.stats_path, encoding="utf-8") as fh:
            return json.load(fh)

    def stats(self) -> dict:
        return self._stats
