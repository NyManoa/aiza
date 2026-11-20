"""Étape 1d — Géométrie du réseau (déterministe).

1. Coordonnées de chaque lieu, avec leur qualité :
     fokontany        moyenne des centroïdes des fokontany rattachés
     commune          point de la commune rattachée
     estimee_voisins  repère non rattaché : moyenne des arrêts voisins sur les trajets publiés (itérée)
     centre_ville     gare « Antananarivo (…) » non rattachée : centre-ville (Analakely), approximation explicite
     inconnue         aucune estimation possible
2. Longueur de chaque tronçon urbain (vol d'oiseau entre arrêts consécutifs).
3. Fokontany traversés entre deux arrêts consécutifs :
     declare          saisi dans data/reference/line_fokontany.csv (prioritaire, y compris suburbain)
     corridor_estime  plus court chemin dans le graphe de voisinage des fokontany (mdg_adminlines), pondéré par la
                      distance entre centroïdes ; rejeté s'il est trop sinueux. JAMAIS pour une liaison suburbaine
                      (aucun arrêt intermédiaire n'est inventé).

Sorties (data/processed/tables/) : place_geometry.csv, line_corridors.csv, line_fokontany_suggestions.csv
"""
from __future__ import annotations

import csv
import heapq
import json
from collections import defaultdict

import pandas as pd

from planner import rules
from planner.core.geo import haversine_km
from planner.core.text import norm
from planner.settings import get_settings

LINE_FOKONTANY_CSV = "line_fokontany.csv"


def _load():
    d = get_settings().tables_dir
    t = {n: pd.read_csv(d / f"{n}.csv") for n in
         ("places", "place_admin_matches", "route_steps", "line_variants", "lines", "suburban_links",
          "admin4", "admin3", "fokontany_neighbors")}
    return t


def place_coordinates(t: dict) -> dict[str, dict]:
    a4 = t["admin4"].set_index("adm4_pcode")
    a3 = t["admin3"].set_index("adm3_pcode")
    m = t["place_admin_matches"]
    out: dict[str, dict] = {}
    for pid, g in m.groupby("place_id"):
        fks = [c for c in g.adm4_pcode.dropna() if c in a4.index]
        coms = [c for c in g.adm3_pcode.dropna() if c in a3.index]
        lvl = g.level.iloc[0]
        if lvl == "fokontany" and fks:
            pts = [(a4.loc[c].lat, a4.loc[c].lon) for c in fks]
            q = "fokontany"
        elif lvl == "commune" and coms:
            pts = [(a3.loc[c].lat, a3.loc[c].lon) for c in coms if pd.notna(a3.loc[c].lat)]
            q = "commune"
        else:
            pts, q = [], "inconnue"
        if pts:
            out[pid] = {"lat": sum(a for a, _ in pts) / len(pts), "lon": sum(b for _, b in pts) / len(pts), "quality": q}
        else:
            out[pid] = {"lat": None, "lon": None, "quality": "inconnue"}

    # Interpolation des repères à partir des arrêts voisins (trajets urbains publiés).
    nb: dict[str, set[str]] = defaultdict(set)
    for _, g in t["route_steps"].groupby("variant_id"):
        seqs = [list(gg.place_id) for _, gg in g.groupby("seq", sort=True)]
        for a, b in zip(seqs, seqs[1:], strict=False):
            for x in a:
                for y in b:
                    if x != y:
                        nb[x].add(y)
                        nb[y].add(x)
    for _ in range(rules.COORD_ESTIMATION_ROUNDS):
        changed = False
        for pid in sorted(out):
            if out[pid]["lat"] is not None:
                continue
            pts = [out[n] for n in sorted(nb.get(pid, ())) if out.get(n, {}).get("lat") is not None]
            if pts:
                out[pid] = {"lat": sum(p["lat"] for p in pts) / len(pts), "lon": sum(p["lon"] for p in pts) / len(pts),
                            "quality": "estimee_voisins"}
                changed = True
        if not changed:
            break
    # Gare « Antananarivo (X) » toujours inconnue : centre-ville (approximation déclarée).
    ctx = t["places"].set_index("place_id").contexts
    for pid, v in out.items():
        if v["lat"] is None and isinstance(ctx.get(pid), str) and "Antananarivo" in ctx.get(pid):
            out[pid] = {"lat": rules.CITY_CENTER[0], "lon": rules.CITY_CENTER[1], "quality": "centre_ville"}
    return out


class FokontanyGraph:
    """Graphe de voisinage des fokontany d'Analamanga, pondéré par la distance entre centroïdes."""

    def __init__(self, t: dict) -> None:
        a4 = t["admin4"]
        a4 = a4[a4.adm1_pcode == rules.ANALAMANGA]
        self.pos = {c: (la, lo) for c, la, lo in zip(a4.adm4_pcode, a4.lat, a4.lon, strict=True) if pd.notna(la)}
        self.tier_ok = set(a4[a4.adm2_pcode.isin(rules.TIER1_DISTRICTS | rules.TIER2_DISTRICTS)].adm4_pcode)
        self.adj: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for a, b in zip(t["fokontany_neighbors"].adm4_pcode_a, t["fokontany_neighbors"].adm4_pcode_b, strict=True):
            if a in self.pos and b in self.pos:
                w = haversine_km(*self.pos[a], *self.pos[b])
                self.adj[a].append((b, w))
                self.adj[b].append((a, w))
        self._cache: dict[tuple[str, str], tuple[list[str], float] | None] = {}

    def nearest(self, lat: float, lon: float) -> str | None:
        best = min(((haversine_km(lat, lon, *p), c) for c, p in self.pos.items() if c in self.tier_ok), default=None)
        return best[1] if best else None

    def shortest_path(self, a: str, b: str) -> tuple[list[str], float] | None:
        if (a, b) in self._cache:
            return self._cache[(a, b)]
        dist, prev, pq = {a: 0.0}, {}, [(0.0, a)]
        while pq:
            d, u = heapq.heappop(pq)
            if u == b:
                break
            if d > dist.get(u, float("inf")):
                continue
            for v, w in sorted(self.adj.get(u, ())):
                nd = d + w
                if nd < dist.get(v, float("inf")) - 1e-12:
                    dist[v], prev[v] = nd, u
                    heapq.heappush(pq, (nd, v))
        res = None
        if b in dist:
            path, x = [b], b
            while x != a:
                x = prev[x]
                path.append(x)
            res = (path[::-1], dist[b])
        self._cache[(a, b)] = res
        return res


def load_declared(t: dict) -> list[dict]:
    """data/reference/line_fokontany.csv : line_code, variant, from_stop, to_stop, fokontany (Nom@Commune;…), note."""
    path = get_settings().reference_dir / LINE_FOKONTANY_CSV
    if not path.exists():
        return []
    a4 = t["admin4"]
    by_name = {(norm(n), norm(c)): p for n, c, p in zip(a4.adm4_name, a4.adm3_name, a4.adm4_pcode, strict=True)}
    rows = []
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(x for x in fh if x.strip() and not x.lstrip().startswith("#")):
            codes = []
            for item in [x.strip() for x in (r.get("fokontany") or "").split(";") if x.strip()]:
                name, _, com = item.partition("@")
                code = by_name.get((norm(name), norm(com)))
                if not code:
                    raise ValueError(f"{LINE_FOKONTANY_CSV} : fokontany introuvable « {item} »")
                codes.append(code)
            rows.append({**r, "codes": codes})
    return rows


def build() -> dict[str, int]:
    t = _load()
    out_dir = get_settings().tables_dir
    coords = place_coordinates(t)
    fg = FokontanyGraph(t)
    places = t["places"].set_index("place_id")
    m = t["place_admin_matches"]
    fk_of = {pid: [c for c in g.adm4_pcode.dropna()] for pid, g in m.groupby("place_id")}
    a4 = t["admin4"].set_index("adm4_pcode")
    declared = load_declared(t)

    def pos_coord(alts: list[str]) -> tuple[float, float] | None:
        pts = [(coords[p]["lat"], coords[p]["lon"]) for p in alts if coords[p]["lat"] is not None]
        return (sum(a for a, _ in pts) / len(pts), sum(b for _, b in pts) / len(pts)) if pts else None

    def candidates(alts: list[str]) -> tuple[list[str], bool]:
        c = [x for p in alts for x in fk_of.get(p, []) if x in fg.pos]
        if c:
            return c, False
        pc = pos_coord(alts)
        near = fg.nearest(*pc) if pc else None
        return ([near] if near else []), True

    corridor_rows, services_geo = [], {}
    stats = defaultdict(int)
    # ---- services urbains (variantes) ----
    variants = t["line_variants"].set_index("variant_id")
    lines = t["lines"].set_index("line_id")
    for vid, g in t["route_steps"].groupby("variant_id", sort=False):
        positions = [list(gg.place_id) for _, gg in g.sort_values(["seq", "alt_index"]).groupby("seq", sort=True)]
        v = variants.loc[vid]
        line_code = lines.loc[v.line_id].line_code
        seg_km, corridors = [], []
        for i in range(len(positions) - 1):
            a, b = positions[i], positions[i + 1]
            ca, cb = pos_coord(a), pos_coord(b)
            seg_km.append(round(haversine_km(*ca, *cb), 3) if ca and cb else None)
            decl = _declared_for(declared, line_code, v.variant_label, a, b, places)
            if decl is not None:
                corridors.append([{"adm4": c, "source": "declare"} for c in decl])
                stats["troncons_declares"] += 1
            else:
                corridors.append(_estimate(fg, a, b, candidates, stats))
            for rank, e in enumerate(corridors[-1], start=1):
                corridor_rows.append({"service_id": vid, "line_code": line_code, "variant": v.variant_label,
                                      "segment": i + 1, "from_place": " / ".join(places.loc[p].display_name for p in a),
                                      "to_place": " / ".join(places.loc[p].display_name for p in b),
                                      "seg_km": seg_km[-1], "rank": rank, "adm4_pcode": e["adm4"],
                                      "adm4_name": a4.loc[e["adm4"]].adm4_name, "adm3_name": a4.loc[e["adm4"]].adm3_name,
                                      "source": e["source"]})
        services_geo[vid] = {"seg_km": seg_km, "corridor": corridors}
    # ---- liaisons suburbaines : distance directe ; fokontany traversés uniquement s'ils sont déclarés ----
    for k in t["suburban_links"].itertuples():
        a, b = [k.primus_place_id], [k.terminus_place_id]
        ca, cb = pos_coord(a), pos_coord(b)
        decl = _declared_for(declared, lines.loc[k.line_id].line_code, k.terminus_raw, a, b, places)
        corr = [{"adm4": c, "source": "declare"} for c in decl] if decl else []
        services_geo[k.link_id] = {"seg_km": [round(haversine_km(*ca, *cb), 3) if ca and cb else None], "corridor": [corr]}
        for rank, e in enumerate(corr, start=1):
            corridor_rows.append({"service_id": k.link_id, "line_code": lines.loc[k.line_id].line_code,
                                  "variant": k.terminus_raw, "segment": 1, "from_place": k.primus_raw,
                                  "to_place": k.terminus_raw, "seg_km": services_geo[k.link_id]["seg_km"][0], "rank": rank,
                                  "adm4_pcode": e["adm4"], "adm4_name": a4.loc[e["adm4"]].adm4_name,
                                  "adm3_name": a4.loc[e["adm4"]].adm3_name, "source": "declare"})

    geo = pd.DataFrame([{"place_id": p, **v} for p, v in sorted(coords.items())])
    geo.to_csv(out_dir / "place_geometry.csv", index=False)
    cor = pd.DataFrame(corridor_rows, columns=["service_id", "line_code", "variant", "segment", "from_place", "to_place",
                                               "seg_km", "rank", "adm4_pcode", "adm4_name", "adm3_name", "source"])
    cor.to_csv(out_dir / "line_corridors.csv", index=False)
    _write_suggestions(cor, out_dir)
    with open(out_dir / "services_geometry.json", "w", encoding="utf-8") as fh:
        json.dump(services_geo, fh, ensure_ascii=False)
    q = geo.quality.value_counts().to_dict()
    return {**{f"coord_{k}": v for k, v in q.items()}, **dict(stats),
            "fokontany_traverses_distincts": int(cor.adm4_pcode.nunique()) if len(cor) else 0}


def _declared_for(declared, line_code, variant, a, b, places) -> list[str] | None:
    na = {norm(places.loc[p].display_name) for p in a}
    nbs = {norm(places.loc[p].display_name) for p in b}
    for r in declared:
        if norm(r.get("line_code", "")) not in (norm(line_code), norm(f"ligne {line_code}")):
            continue
        var = (r.get("variant") or "*").strip()
        if var not in ("*", "") and norm(var) != norm(variant):
            continue
        f, to = norm(r.get("from_stop", "")), norm(r.get("to_stop", ""))
        if f in na and to in nbs:
            return r["codes"]
        if f in nbs and to in na:
            return list(reversed(r["codes"]))
    return None


def _estimate(fg: FokontanyGraph, a, b, candidates, stats) -> list[dict]:
    ca, est_a = candidates(a)
    cb, est_b = candidates(b)
    if not ca or not cb:
        stats["troncons_sans_estimation"] += 1
        return []
    fa, fb = min(((x, y) for x in ca for y in cb), key=lambda xy: (haversine_km(*fg.pos[xy[0]], *fg.pos[xy[1]]), xy))
    if fa == fb:
        stats["troncons_meme_fokontany"] += 1
        return []
    res = fg.shortest_path(fa, fb)
    direct = haversine_km(*fg.pos[fa], *fg.pos[fb])
    if not res or res[1] > rules.CORRIDOR_MAX_RATIO * direct + rules.CORRIDOR_MARGIN_KM:
        stats["troncons_rejetes_sinueux"] += 1
        return []
    path = res[0]
    # Les extrémités estimées (repères sans fokontany) font partie du passage ; les arrêts rattachés non.
    inner = path[(0 if est_a else 1): (len(path) if est_b else len(path) - 1)]
    stats["troncons_estimes"] += 1
    return [{"adm4": c, "source": "corridor_estime"} for c in inner]


def _write_suggestions(cor: pd.DataFrame, out_dir) -> None:
    """Gabarit pré-rempli au format de data/reference/line_fokontany.csv, à valider sur le terrain."""
    est = cor[cor.source == "corridor_estime"]
    rows = []
    for _key, g in est.groupby(["service_id", "segment"], sort=False):
        r = g.iloc[0]
        rows.append({"line_code": r.line_code, "variant": r.variant, "from_stop": r.from_place.split(" / ")[0],
                     "to_stop": r.to_place.split(" / ")[0],
                     "fokontany": ";".join(f"{n}@{c}" for n, c in zip(g.adm4_name, g.adm3_name, strict=True)),
                     "note": "estimation à valider"})
    pd.DataFrame(rows, columns=["line_code", "variant", "from_stop", "to_stop", "fokontany", "note"]).drop_duplicates(
        ["line_code", "from_stop", "to_stop", "fokontany"]).to_csv(out_dir / "line_fokontany_suggestions.csv", index=False)


if __name__ == "__main__":
    for k, v in build().items():
        print(f"{k:30s} {v}")
