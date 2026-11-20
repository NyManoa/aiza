"""Accès en lecture aux données produites par le pipeline (référentiel administratif + réseau + géométrie).

Chargé une seule fois au démarrage ; immuable ensuite (sûr en environnement multi-thread).

Chaque service est « étendu » : entre deux arrêts publiés sont insérées des positions virtuelles pour les fokontany
traversés (déclarés ou estimés). Une position virtuelle permet de monter/descendre « en passage » (accès signalé,
confiance faible) mais jamais de faire une correspondance.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

from planner import rules
from planner.core.geo import haversine_km
from planner.core.text import norm
from planner.engine.errors import NotFoundError
from planner.engine.models import Position

VIRTUAL_PREFIX = "fk:"


def _float(v: str | None) -> float | None:
    try:
        return float(v) if v not in ("", None) else None
    except ValueError:
        return None


def _split(v: str | None) -> list[str]:
    return [c for c in (v or "").split(";") if c]


def is_virtual(place_id: str) -> bool:
    return place_id.startswith(VIRTUAL_PREFIX)


class NetworkRepository:
    def __init__(self, network_json: Path, tables_dir: Path) -> None:
        with open(network_json, encoding="utf-8") as fh:
            net = json.load(fh)
        self.places: dict[str, dict] = net["places"]
        self.lines: dict[str, dict] = net["lines"]
        self.services: list[dict] = net["services"]
        self.served: dict[str, list[dict]] = net["served"]
        self.neighbors: dict[str, list[str]] = net["neighbors"]
        self.meta: dict = net["meta"]
        self._load_admin(tables_dir)
        self._add_virtual_places()
        self._expand_services()
        self._index()

    # ------------------------------------------------------------------ chargement
    def _load_admin(self, d: Path) -> None:
        def read(name: str) -> list[dict]:
            with open(d / name, encoding="utf-8") as fh:
                return list(csv.DictReader(fh))

        self.regions = {r["adm1_pcode"]: r for r in read("admin1.csv")}
        self.districts = {r["adm2_pcode"]: r for r in read("admin2.csv")}
        self.communes = {r["adm3_pcode"]: r for r in read("admin3.csv")}
        self.fokontany = {r["adm4_pcode"]: r for r in read("admin4.csv")}
        for table in (self.regions, self.districts, self.communes, self.fokontany):
            for r in table.values():
                r["area_sqkm"] = _float(r.get("area_sqkm"))
        for table in (self.communes, self.fokontany):
            for r in table.values():
                r["lat"], r["lon"] = _float(r.get("lat")), _float(r.get("lon"))
        for r in self.fokontany.values():
            r["_key"] = norm(r["adm4_name"])
        self.children: dict[str, list[str]] = defaultdict(list)
        for r in self.districts.values():
            self.children[r["adm1_pcode"]].append(r["adm2_pcode"])
        for r in self.communes.values():
            self.children[r["adm2_pcode"]].append(r["adm3_pcode"])
        for r in self.fokontany.values():
            self.children[r["adm3_pcode"]].append(r["adm4_pcode"])

    def _add_virtual_places(self) -> None:
        for code, lst in self.served.items():
            for e in lst:
                if e["mode"] != "passage" or e["place"] in self.places:
                    continue
                f = self.fokontany[code]
                declared = e["status"] == "passage_declare"
                self.places[e["place"]] = {
                    "place_id": e["place"], "name": f"{f['adm4_name']} (passage)", "match_status": e["status"],
                    "match_rule": e["status"], "match_level": "fokontany", "confidence": e["confidence"],
                    "match_detail": ("fokontany traversé déclaré (line_fokontany.csv)" if declared else
                                     "fokontany probablement traversé entre deux arrêts publiés (plus court chemin de "
                                     "voisinage) — montée/descente à confirmer"),
                    "fokontany": code, "communes": f["adm3_pcode"], "lat": f["lat"], "lon": f["lon"],
                    "coord_quality": "fokontany", "n_lines": 0, "virtual": True,
                }

    def _expand_services(self) -> None:
        """positions[si] : arrêts publiés + fokontany traversés, avec distance cumulée."""
        self.positions: list[list[Position]] = []
        for s in self.services:
            stops, seg_km, corridor = s["stops"], s.get("seg_km") or [], s.get("corridor") or []
            pos: list[Position] = []
            cum, unk = 0.0, 0
            for i, alts in enumerate(stops):
                pos.append(Position(tuple(alts), True, round(cum, 4), unk))
                if i == len(stops) - 1:
                    break
                seg = seg_km[i] if i < len(seg_km) else None
                if seg is None:
                    seg = rules.DEFAULT_SEGMENT_KM if s["stops_known"] else rules.DEFAULT_SUBURBAN_KM
                    unk += 1
                cor = corridor[i] if i < len(corridor) else []
                for k, e in enumerate(cor, start=1):
                    pos.append(Position((VIRTUAL_PREFIX + e["adm4"],), False, round(cum + seg * k / (len(cor) + 1), 4), unk))
                cum += seg
            self.positions.append(pos)

    def _index(self) -> None:
        self.place_positions: dict[str, list[tuple[int, int]]] = defaultdict(list)
        lines_of: dict[str, set[str]] = defaultdict(set)
        for si, pos in enumerate(self.positions):
            for k, p in enumerate(pos):
                for pid in p.places:
                    self.place_positions[pid].append((si, k))
                    lines_of[pid].add(self.services[si]["line_id"])
        for pid, p in self.places.items():
            if p.get("virtual"):
                p["n_lines"] = len(lines_of[pid])
        # Correspondance à pied : lieux réels partageant un fokontany de rattachement direct.
        by_fk: dict[str, set[str]] = defaultdict(set)
        for code, lst in self.served.items():
            for e in lst:
                if e["mode"] == "direct":
                    by_fk[code].add(e["place"])
        self.walk: dict[str, set[str]] = defaultdict(set)
        self.walk_fk: dict[tuple[str, str], str] = {}
        for code, ps in sorted(by_fk.items()):
            for a in ps:
                for b in ps:
                    if a != b:
                        self.walk[a].add(b)
                        self.walk_fk.setdefault((a, b), code)
        self.direct_served = {c for c, lst in self.served.items() if any(e["mode"] == "direct" for e in lst)}

    # ------------------------------------------------------------------ géométrie
    def place_coord(self, pid: str) -> tuple[float, float] | None:
        p = self.places.get(pid)
        if not p or p.get("lat") is None:
            return None
        return (p["lat"], p["lon"])

    def fokontany_coord(self, adm4: str) -> tuple[float, float] | None:
        f = self.fokontany.get(adm4)
        return (f["lat"], f["lon"]) if f and f["lat"] is not None else None

    def walk_km(self, a: str, b: str) -> float:
        ca, cb = self.place_coord(a), self.place_coord(b)
        if ca and cb:
            return max(round(haversine_km(*ca, *cb), 3), rules.WALK_TRANSFER_DEFAULT_KM / 2)
        return rules.WALK_TRANSFER_DEFAULT_KM

    # ------------------------------------------------------------------ accès
    def require_fokontany(self, adm4: str) -> dict:
        try:
            return self.fokontany[adm4]
        except KeyError:
            raise NotFoundError(f"pcode de fokontany inconnu : {adm4}") from None

    def admin_label(self, adm4: str) -> dict:
        f = self.require_fokontany(adm4)
        return {"adm4_pcode": adm4, "adm4_name": f["adm4_name"], "adm3_pcode": f["adm3_pcode"],
                "adm3_name": f["adm3_name"], "adm2_pcode": f["adm2_pcode"], "adm2_name": f["adm2_name"],
                "adm1_pcode": f["adm1_pcode"], "adm1_name": f["adm1_name"], "area_sqkm": f["area_sqkm"],
                "lat": f["lat"], "lon": f["lon"]}

    def place_summary(self, pid: str) -> dict:
        p = self.places[pid]
        return {"place_id": pid, "name": p["name"], "match_status": p["match_status"],
                "confidence": p["confidence"], "fokontany": _split(p["fokontany"]),
                "communes": _split(p["communes"]), "match_detail": p["match_detail"], "n_lines": p["n_lines"],
                "virtual": bool(p.get("virtual")), "lat": p.get("lat"), "lon": p.get("lon"),
                "coord_quality": p.get("coord_quality", "inconnue")}

    def served_summary(self, adm4: str) -> dict:
        lst = self.served.get(adm4, [])
        direct = [e for e in lst if e["mode"] == "direct"]
        passage = [e for e in lst if e["mode"] == "passage"]
        lines = {self.services[si]["line_id"] for e in lst for si, _ in self.place_positions.get(e["place"], [])}
        best = lst[0] if lst else None
        coverage = ("direct" if direct else "commune" if any(e["mode"] == "commune" for e in lst)
                    else "passage" if passage else "aucune")
        return {"n_places": len(lst), "n_direct": len(direct), "n_passage": len(passage), "n_lines": len(lines),
                "best_status": best["status"] if best else "non_desservi",
                "best_confidence": best["confidence"] if best else 0.0, "coverage": coverage}

    def position_label(self, si: int, k: int) -> str:
        return " / ".join(self.places[p]["name"] for p in self.positions[si][k].places)

    def stop_label(self, service: dict, pos: int) -> str:
        return " / ".join(self.places[p]["name"] for p in service["stops"][pos])

    def lines_at(self, place_ids: dict[str, float]) -> list[dict]:
        """Services passant par des lieux (triés par confiance décroissante), avec leurs extrémités publiées."""
        out, seen = [], set()
        for pid in sorted(place_ids, key=lambda p: (-place_ids[p], p)):
            for si, _ in self.place_positions.get(pid, []):
                s = self.services[si]
                if s["id"] in seen:
                    continue
                seen.add(s["id"])
                ends = s["stops"][0] + s["stops"][-1]
                out.append({"service_id": s["id"], "line_code": s["line_code"], "zone": s["zone"],
                            "variant": s["label"], "place": self.places[pid]["name"],
                            "from": self.stop_label(s, 0), "to": self.stop_label(s, -1),
                            "passage": is_virtual(pid),
                            "other_end_unresolved": any(self.places[x]["match_status"] == "non_resolu"
                                                        for x in ends if x != pid)})
        return out
