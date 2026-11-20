"""Étape 2a — Graphe orienté du réseau + bundle applicatif.

Nœuds  : lieux du corpus (arrêts urbains, primus, terminus).
Arcs   : - urbain    : arrêts consécutifs d'une variante, dans le sens publié ("aller") ;
                       sens inverse ajouté pour les variantes non circulaires ("retour_suppose", signalé) ;
         - suburbain : Primus -> Terminus ("aller") et Terminus -> Primus ("retour_suppose"),
                       SANS aucun arrêt intermédiaire (non fournis par la source).
Sorties (graph/output/) :
  nodes.csv, edges.csv, node_metrics.csv, network.json (consommé par router/)
"""
from __future__ import annotations

import json
from collections import defaultdict

import pandas as pd

from planner import rules
from planner.settings import get_settings


def _clean(v):
    if isinstance(v, float) and pd.isna(v):
        return None
    if hasattr(v, "item"):
        return v.item()
    return v


def load_tables() -> dict[str, pd.DataFrame]:
    d = get_settings().tables_dir
    return {n: pd.read_csv(d / f"{n}.csv") for n in
            ("lines", "line_variants", "route_steps", "suburban_links", "places", "place_admin_matches",
             "admin4_analamanga", "fokontany_neighbors", "admin3", "admin4")}


def load_geometry() -> tuple[dict, pd.DataFrame]:
    d = get_settings().tables_dir
    with open(d / "services_geometry.json", encoding="utf-8") as fh:
        services_geo = json.load(fh)
    return services_geo, pd.read_csv(d / "place_geometry.csv").set_index("place_id")


def build_services(t: dict[str, pd.DataFrame], services_geo: dict | None = None) -> list[dict]:
    services_geo = services_geo or {}
    lines = t["lines"].set_index("line_id")
    services = []
    steps = t["route_steps"].sort_values(["variant_id", "seq", "alt_index"])
    by_var = {vid: g for vid, g in steps.groupby("variant_id")}
    for v in t["line_variants"].itertuples():
        g = by_var[v.variant_id]
        stops = [list(gg.place_id) for _, gg in g.groupby("seq", sort=True)]
        ln = lines.loc[v.line_id]
        services.append({
            "id": v.variant_id, "line_id": v.line_id, "line_code": ln.line_code, "zone": "urbaine",
            "label": v.variant_label, "sector": _clean(v.sector), "color": _clean(v.color),
            "note": _clean(ln.note), "loop": bool(v.is_loop), "stops": stops,
            "stops_known": True, "via_mention": None, "raw": v.raw_text,
            **services_geo.get(v.variant_id, {"seg_km": [None] * (len(stops) - 1), "corridor": [[]] * (len(stops) - 1)}),
        })
    for k in t["suburban_links"].itertuples():
        ln = lines.loc[k.line_id]
        services.append({
            "id": k.link_id, "line_id": k.line_id, "line_code": ln.line_code, "zone": "suburbaine",
            "label": f"{k.primus_raw} -> {k.terminus_raw}", "sector": None, "color": None, "note": None,
            "loop": False, "stops": [[k.primus_place_id], [k.terminus_place_id]],
            "stops_known": False, "via_mention": _clean(k.via_mention),
            "raw": f"Primus : {k.primus_raw} -> Terminus : {k.terminus_raw}",
            **services_geo.get(k.link_id, {"seg_km": [None], "corridor": [[]]}),
        })
    return services


def build_edges(services: list[dict]) -> pd.DataFrame:
    rows = []
    for s in services:
        kind = "urbain" if s["zone"] == "urbaine" else "suburbain"
        for i in range(len(s["stops"]) - 1):
            for a in s["stops"][i]:
                for b in s["stops"][i + 1]:
                    if a == b:
                        continue
                    rows.append({"source": a, "target": b, "line_id": s["line_id"], "service_id": s["id"],
                                 "kind": kind, "direction": "aller", "seq": i + 1})
                    if not s["loop"]:
                        rows.append({"source": b, "target": a, "line_id": s["line_id"], "service_id": s["id"],
                                     "kind": kind, "direction": "retour_suppose", "seq": i + 1})
    return pd.DataFrame(rows)


def served_index(t: dict[str, pd.DataFrame]) -> dict[str, list[dict]]:
    """adm4_pcode -> lieux qui le desservent (direct = rattachement fokontany ; commune = rattachement communal)."""
    m = t["place_admin_matches"]
    a4 = t["admin4"]
    out: dict[str, list[dict]] = defaultdict(list)
    for r in m[m.level == "fokontany"].itertuples():
        out[r.adm4_pcode].append({"place": r.place_id, "mode": "direct", "status": r.status,
                                  "confidence": float(r.confidence)})
    com = m[m.level == "commune"]
    if not com.empty:
        fk_by_com = a4[a4.adm3_pcode.isin(set(com.adm3_pcode))].groupby("adm3_pcode").adm4_pcode.apply(list).to_dict()
        for r in com.itertuples():
            for code in fk_by_com.get(r.adm3_pcode, []):
                out[code].append({"place": r.place_id, "mode": "commune", "status": r.status,
                                  "confidence": float(r.confidence)})
    return dict(out)


def add_passages(served: dict[str, list[dict]], services: list[dict]) -> int:
    """Fokontany traversés (déclarés ou estimés) : accès « en passage » via un lieu virtuel fk:<pcode>."""
    n = 0
    for s in services:
        for seg in s["corridor"]:
            for e in seg:
                lst = served.setdefault(e["adm4"], [])
                vid = f"fk:{e['adm4']}"
                status = "passage_declare" if e["source"] == "declare" else "passage_estime"
                conf = rules.DECLARED_CORRIDOR_CONFIDENCE if e["source"] == "declare" else rules.CORRIDOR_CONFIDENCE
                cur = next((x for x in lst if x["place"] == vid), None)
                if cur is None:
                    lst.append({"place": vid, "mode": "passage", "status": status, "confidence": conf})
                    n += 1
                elif conf > cur["confidence"]:
                    cur.update(status=status, confidence=conf)
    for code in served:
        served[code].sort(key=lambda x: (-x["confidence"], x["place"]))
    return n


def build() -> dict[str, int]:
    get_settings().graph_dir.mkdir(parents=True, exist_ok=True)
    t = load_tables()
    services_geo, geo = load_geometry()
    services = build_services(t, services_geo)
    edges = build_edges(services)
    edges.to_csv(get_settings().graph_dir / "edges.csv", index=False)

    places = t["places"].set_index("place_id")
    matches = t["place_admin_matches"]

    # --- métriques de nœuds ---------------------------------------------------
    declared = edges[edges.direction == "aller"]
    lines_by_place: dict[str, set] = defaultdict(set)
    services_by_place: dict[str, set] = defaultdict(set)
    passages: dict[str, int] = defaultdict(int)
    for s in services:
        for pos in s["stops"]:
            for pid in pos:
                lines_by_place[pid].add(s["line_id"])
                services_by_place[pid].add(s["id"])
                passages[pid] += 1
    node_rows = []
    for pid, p in places.iterrows():
        mm = matches[matches.place_id == pid]
        fks = [c for c in mm.adm4_pcode.dropna()]
        coms = sorted(set(mm.adm3_pcode.dropna()))
        g = geo.loc[pid] if pid in geo.index else None
        lat = round(float(g.lat), 6) if g is not None and pd.notna(g.lat) else None
        lon = round(float(g.lon), 6) if g is not None and pd.notna(g.lon) else None
        coord_quality = g.quality if g is not None else "inconnue"
        node_rows.append({
            "place_id": pid, "name": p.display_name, "match_status": p.match_status, "match_rule": p.match_rule,
            "match_level": p.match_level, "confidence": p.match_confidence, "match_detail": p.match_detail,
            "fokontany": ";".join(fks), "communes": ";".join(coms), "lat": lat, "lon": lon, "coord_quality": coord_quality,
            "in_degree": int(declared[declared.target == pid].source.nunique()),
            "out_degree": int(declared[declared.source == pid].target.nunique()),
            "n_lines": len(lines_by_place[pid]), "n_services": len(services_by_place[pid]),
            "n_passages": passages[pid], "zones": p.zones, "roles": p.roles,
        })
    nodes = pd.DataFrame(node_rows).sort_values(["n_lines", "n_passages"], ascending=False)
    nodes.to_csv(get_settings().graph_dir / "nodes.csv", index=False)
    nodes[["place_id", "name", "in_degree", "out_degree", "n_lines", "n_services", "n_passages", "match_status",
           "confidence"]].to_csv(get_settings().graph_dir / "node_metrics.csv", index=False)

    # --- composantes faiblement connexes (BFS) ----------------------------------
    adj: dict[str, set] = defaultdict(set)
    for a, b in zip(edges.source, edges.target, strict=True):
        adj[a].add(b)
        adj[b].add(a)
    seen, comps = set(), []
    for n in nodes.place_id:
        if n in seen:
            continue
        stack, comp = [n], []
        seen.add(n)
        while stack:
            x = stack.pop()
            comp.append(x)
            for y in adj[x]:
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        comps.append(sorted(comp))
    comps.sort(key=len, reverse=True)

    # --- bundle applicatif ------------------------------------------------------
    nb = defaultdict(list)
    for a, b in zip(t["fokontany_neighbors"].adm4_pcode_a, t["fokontany_neighbors"].adm4_pcode_b, strict=True):
        nb[a].append(b)
        nb[b].append(a)
    lines_meta = {r.line_id: {"line_id": r.line_id, "line_code": r.line_code, "zone": r.zone,
                              "group": _clean(r.group), "note": _clean(r.note), "n_variants": int(r.n_variants)}
                  for r in t["lines"].itertuples()}
    served = served_index(t)
    n_passages = add_passages(served, services)
    network = {
        "meta": {"generated_by": "planner.pipeline.graph",
                 "n_passage_entries": n_passages, "n_places": len(nodes), "n_services": len(services),
                 "n_edges": len(edges), "components": [len(c) for c in comps]},
        "places": {r["place_id"]: {k: _clean(v) for k, v in r.items()} for r in node_rows},
        "lines": lines_meta,
        "services": services,
        "served": served,
        "neighbors": dict(nb),
        "components": comps,
    }
    with open(get_settings().network_json, "w", encoding="utf-8") as fh:
        json.dump(network, fh, ensure_ascii=False, separators=(",", ":"))
    return {"noeuds": len(nodes), "arcs": len(edges), "arcs_publies": len(declared),
            "services": len(services), "composantes": len(comps), "plus_grande_composante": len(comps[0]),
            "fokontany_desservis_index": len(network["served"]), "acces_en_passage": n_passages}


if __name__ == "__main__":
    for k, v in build().items():
        print(f"{k:28s} {v}")
