"""Étape 2b — Data Analysis : statistiques descriptives et couverture.

Entrées : data/output/*.csv, graph/output/network.json
Sorties (analysis/output/) :
  stats.json                    tout ce qu'affiche l'onglet « Data Analysis & Couverture »
  coverage_fokontany.csv        couverture fokontany par fokontany (Analamanga)
  coverage_by_district.csv      agrégats district / arrondissement
  coverage_by_commune.csv       agrégats commune
  report.md                     rapport lisible
"""
from __future__ import annotations

import json
from collections import defaultdict

import pandas as pd

from planner import rules
from planner.settings import get_settings

LOW_SERVICE_MAX_LINES = rules.LOW_SERVICE_MAX_LINES  # « faible desserte » : au plus 1 ligne directe
COVERAGE_ORDER = ["direct", "faible", "passage", "commune", "aucune"]


def _r(x, n=1):
    return round(float(x), n)


def _sanitize(o):
    """NaN/inf -> None : le JSON produit doit rester strictement valide (navigateurs)."""
    if isinstance(o, float) and (o != o or o in (float("inf"), float("-inf"))):
        return None
    if isinstance(o, dict):
        return {k: _sanitize(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_sanitize(v) for v in o]
    return o


def build() -> dict:
    out = get_settings().analysis_dir
    out.mkdir(parents=True, exist_ok=True)
    with open(get_settings().network_json, encoding="utf-8") as fh:
        net = json.load(fh)
    places = pd.read_csv(get_settings().tables_dir / "places.csv")
    steps = pd.read_csv(get_settings().tables_dir / "route_steps.csv")
    links = pd.read_csv(get_settings().tables_dir / "suburban_links.csv")
    lines = pd.read_csv(get_settings().tables_dir / "lines.csv")
    variants = pd.read_csv(get_settings().tables_dir / "line_variants.csv")
    fk = pd.read_csv(get_settings().tables_dir / "admin4_analamanga.csv")
    nodes = pd.read_csv(get_settings().graph_dir / "nodes.csv")
    geo = pd.read_csv(get_settings().tables_dir / "place_geometry.csv")
    cor = pd.read_csv(get_settings().tables_dir / "line_corridors.csv")
    edges = pd.read_csv(get_settings().graph_dir / "edges.csv")

    services = net["services"]
    lines_of_place = defaultdict(set)
    for svc in services:
        for pos in svc["stops"]:
            for pid in pos:
                lines_of_place[pid].add(svc["line_id"])
        for seg in svc.get("corridor", []):
            for e in seg:
                lines_of_place["fk:" + e["adm4"]].add(svc["line_id"])

    # ---------------------------------------------------------------- 1. rattachement
    status_order = ["exact_fokontany", "sous_chaine_fokontany", "commune", "repere_ou_variante", "non_resolu"]
    st_places = places.match_status.value_counts().reindex(status_order, fill_value=0)
    occ = pd.concat([steps[["place_id"]], links[["primus_place_id"]].rename(columns={"primus_place_id": "place_id"}),
                     links[["terminus_place_id"]].rename(columns={"terminus_place_id": "place_id"})])
    occ = occ.merge(places[["place_id", "match_status"]], on="place_id")
    st_occ = occ.match_status.value_counts().reindex(status_order, fill_value=0)
    resolved_places = int((places.match_status != "non_resolu").sum())
    resolved_occ = int((occ.match_status != "non_resolu").sum())
    conf_bins = pd.cut(places.match_confidence, [-0.01, 0.0, 0.5, 0.7, 0.9, 1.0],
                       labels=["0 (non résolu)", "0.01–0.50", "0.51–0.70", "0.71–0.90", "0.91–1.00"])
    matching = {
        "n_places": len(places),
        "resolved_places": resolved_places,
        "resolved_places_pct": _r(100 * resolved_places / len(places)),
        "n_occurrences": len(occ),
        "resolved_occurrences": resolved_occ,
        "resolved_occurrences_pct": _r(100 * resolved_occ / len(occ)),
        "by_status_places": st_places.to_dict(),
        "by_status_occurrences": st_occ.to_dict(),
        "confidence_distribution": conf_bins.value_counts().sort_index().to_dict(),
        "unresolved": (places[places.match_status == "non_resolu"]
                       .assign(n_lines=lambda d: d.place_id.map(lambda p: len(lines_of_place[p])))
                       .sort_values(["occurrences", "n_lines"], ascending=False)
                       [["place_id", "display_name", "occurrences", "n_lines", "roles"]]
                       .rename(columns={"display_name": "name"}).to_dict("records")),
    }

    # ---------------------------------------------------------------- 2. réseau / graphe
    declared = edges[edges.direction == "aller"]
    hubs = nodes.sort_values(["n_lines", "n_passages"], ascending=False)
    network = {
        "urban_lines": int((lines.zone == "urbaine").sum()),
        "urban_variants": len(variants),
        "loop_variants": int(variants.is_loop.sum()),
        "suburban_groups": int((lines.zone == "suburbaine").sum()),
        "suburban_links": len(links),
        "nodes": len(nodes), "edges_total": len(edges), "edges_declared": len(declared),
        "edges_reverse_assumed": int((edges.direction == "retour_suppose").sum()),
        "components": net["meta"]["components"],
        "isolated_components": [c for c in net["components"][1:]],
        "variants_by_label": variants.variant_label.value_counts().head(12).to_dict(),
        "suburban_links_by_group": links.line_id.value_counts().sort_index().to_dict(),
        "top_nodes_by_lines": hubs.head(20)[["place_id", "name", "n_lines", "n_services", "n_passages", "in_degree",
                                             "out_degree", "match_status", "confidence"]].to_dict("records"),
        "top_nodes_by_passages": nodes.sort_values("n_passages", ascending=False).head(15)[
            ["place_id", "name", "n_passages", "n_lines"]].to_dict("records"),
        "transfer_nodes": int((nodes.n_lines >= 2).sum()),
        "coord_quality": geo.quality.value_counts().to_dict(),
        "corridor_segments": {"estimes": int(cor[cor.source == "corridor_estime"][["service_id", "segment"]]
                                             .drop_duplicates().shape[0]),
                              "declares": int(cor[cor.source == "declare"][["service_id", "segment"]]
                                              .drop_duplicates().shape[0]),
                              "fokontany_distincts": int(cor.adm4_pcode.nunique())},
        "network_length_km": round(sum(x for svc in services if svc["zone"] == "urbaine"
                                       for x in svc.get("seg_km", []) if x is not None), 1),
        "lines_per_node_distribution": nodes.n_lines.value_counts().sort_index().to_dict(),
    }

    # ---------------------------------------------------------------- 3. couverture fokontany
    served = net["served"]
    rows = []
    for r in fk.itertuples():
        lst = served.get(r.adm4_pcode, [])
        direct = [e for e in lst if e["mode"] == "direct"]
        l_direct = set().union(*[lines_of_place[e["place"]] for e in direct]) if direct else set()
        l_all = set().union(*[lines_of_place[e["place"]] for e in lst]) if lst else set()
        passage = [e for e in lst if e["mode"] == "passage"]
        l_passage = set().union(*[lines_of_place[e["place"]] for e in passage]) if passage else set()
        if direct:
            cov = "faible" if len(l_direct) <= LOW_SERVICE_MAX_LINES else "direct"
        elif any(e["mode"] == "commune" for e in lst):
            cov = "commune"
        elif passage:
            cov = "passage"
        else:
            cov = "aucune"
        rows.append({
            "adm4_pcode": r.adm4_pcode, "adm4_name": r.adm4_name, "adm3_pcode": r.adm3_pcode, "adm3_name": r.adm3_name,
            "adm2_pcode": r.adm2_pcode, "adm2_name": r.adm2_name, "tier": r.tier, "area_sqkm": r.area_sqkm,
            "n_places_direct": len(direct), "n_places_commune": len(lst) - len(direct) - len(passage),
            "n_lines_passage": len(l_passage),
            "n_lines_direct": len(l_direct), "n_lines_total": len(l_all),
            "best_confidence": max([e["confidence"] for e in lst], default=0.0),
            "best_status": lst[0]["status"] if lst else "non_desservi",
            "coverage": cov,
        })
    cov = pd.DataFrame(rows)
    # Distance (en anneaux de voisinage) au fokontany desservi directement le plus proche
    nb = net["neighbors"]
    direct_set = set(cov[cov.coverage.isin(["direct", "faible"])].adm4_pcode)
    ring = {}
    frontier = list(direct_set)
    for c in frontier:
        ring[c] = 0
    k = 0
    while frontier and k < 6:
        k += 1
        nxt = []
        for c in frontier:
            for n in nb.get(c, []):
                if n not in ring:
                    ring[n] = k
                    nxt.append(n)
        frontier = nxt
    cov["rings_to_network"] = cov.adm4_pcode.map(ring)
    cov.to_csv(out / "coverage_fokontany.csv", index=False)

    def agg(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
        g = df.groupby(keys)
        res = pd.DataFrame({
            "n_fokontany": g.size(),
            "direct": g.apply(lambda d: int((d.coverage == "direct").sum()), include_groups=False),
            "faible": g.apply(lambda d: int((d.coverage == "faible").sum()), include_groups=False),
            "commune": g.apply(lambda d: int((d.coverage == "commune").sum()), include_groups=False),
            "passage": g.apply(lambda d: int((d.coverage == "passage").sum()), include_groups=False),
            "aucune": g.apply(lambda d: int((d.coverage == "aucune").sum()), include_groups=False),
            "area_sqkm": g.area_sqkm.sum().round(2),
            "area_direct_sqkm": g.apply(lambda d: d[d.coverage.isin(["direct", "faible"])].area_sqkm.sum(),
                                        include_groups=False).round(2),
            "mean_lines_direct": g.n_lines_direct.mean().round(2),
        }).reset_index()
        res["pct_fokontany_direct"] = (100 * (res.direct + res.faible) / res.n_fokontany).round(1)
        res["pct_area_direct"] = (100 * res.area_direct_sqkm / res.area_sqkm).round(1)
        return res

    by_d = agg(cov, ["adm2_pcode", "adm2_name", "tier"]).sort_values(["tier", "adm2_name"])
    by_c = agg(cov, ["adm2_name", "adm3_pcode", "adm3_name", "tier"]).sort_values(["tier", "adm2_name", "adm3_name"])
    by_d.to_csv(out / "coverage_by_district.csv", index=False)
    by_c.to_csv(out / "coverage_by_commune.csv", index=False)

    bins = pd.cut(cov.n_lines_direct, [-1, 0, 1, 2, 5, 10, 1000], labels=["0", "1", "2", "3–5", "6–10", ">10"])
    core = cov[cov.tier <= 2]
    coverage = {
        "n_fokontany": len(cov),
        "by_coverage": cov.coverage.value_counts().reindex(COVERAGE_ORDER, fill_value=0).to_dict(),
        "by_coverage_core": core.coverage.value_counts().reindex(COVERAGE_ORDER, fill_value=0).to_dict(),
        "n_core": len(core),
        "lines_per_fokontany_distribution": bins.value_counts().sort_index().to_dict(),
        "lines_per_fokontany_distribution_core": pd.cut(core.n_lines_direct, [-1, 0, 1, 2, 5, 10, 1000],
                                                        labels=["0", "1", "2", "3–5", "6–10", ">10"]).value_counts().sort_index().to_dict(),
        "by_district": by_d.to_dict("records"),
        "by_commune_core": by_c[by_c.tier <= 2].to_dict("records"),
        "top_fokontany_by_lines": cov.sort_values(["n_lines_direct", "best_confidence"], ascending=False).head(15)[
            ["adm4_pcode", "adm4_name", "adm3_name", "n_lines_direct", "best_status", "best_confidence"]].to_dict("records"),
        "unserved_core_largest": core[core.coverage == "aucune"].sort_values("area_sqkm", ascending=False).head(25)[
            ["adm4_pcode", "adm4_name", "adm3_name", "adm2_name", "area_sqkm", "rings_to_network"]].to_dict("records"),
        "unserved_urban": cov[(cov.tier == 1) & (cov.coverage.isin(["aucune", "commune", "passage"]))].sort_values(
            ["adm2_name", "adm4_name"])[["adm4_pcode", "adm4_name", "adm3_name", "coverage", "rings_to_network",
                                         "area_sqkm"]].to_dict("records"),
        "low_service_core": core[core.coverage == "faible"].sort_values("area_sqkm", ascending=False).head(25)[
            ["adm4_pcode", "adm4_name", "adm3_name", "n_lines_direct", "best_status"]].to_dict("records"),
        "rings_distribution_core": core.rings_to_network.fillna(-1).astype(int).value_counts().sort_index()
                                       .rename(index={-1: "> 6 ou isolé"}).to_dict(),
        "confidence_of_served": cov[cov.coverage != "aucune"].best_status.value_counts().to_dict(),
    }

    stats = {"matching": matching, "network": network, "coverage": coverage,
             "params": {"low_service_max_lines": LOW_SERVICE_MAX_LINES,
                        "tiers": {"1": "Antananarivo Renivohitra (6 arrondissements)",
                                  "2": "Périphérie : Atsimondrano, Avaradrano, Ambohidratrimo",
                                  "3": "Reste d'Analamanga"}}}
    stats = _sanitize(json.loads(json.dumps(stats, default=lambda o: o.item() if hasattr(o, "item") else str(o))))
    with open(out / "stats.json", "w", encoding="utf-8") as fh:
        json.dump(stats, fh, ensure_ascii=False, indent=1, allow_nan=False)
    (out / "report.md").write_text(render_report(stats), encoding="utf-8")
    return stats


def render_report(s: dict) -> str:
    m, n, c = s["matching"], s["network"], s["coverage"]
    L = ["# Rapport d'analyse — réseau de transport d'Antananarivo", "",
         "_Généré par `analysis/stats.py` (règles déterministes, aucune IA)._", "",
         "## 1. Rattachement lieux ↔ référentiel administratif", "",
         f"- Lieux uniques du corpus : **{m['n_places']}** — rattachés : **{m['resolved_places']}** ({m['resolved_places_pct']} %)",
         f"- Occurrences (passages dans les trajets/liaisons) : **{m['n_occurrences']}** — rattachées : "
         f"**{m['resolved_occurrences']}** ({m['resolved_occurrences_pct']} %)", "",
         "| Statut | Lieux | Occurrences |", "|---|---:|---:|"]
    for k in m["by_status_places"]:
        L.append(f"| {k} | {m['by_status_places'][k]} | {m['by_status_occurrences'][k]} |")
    L += ["", "Lieux non résolus (priorité de complétion de `data/reference/manual_places.csv`) :", ""]
    L += [f"- {u['name']} — {u['occurrences']} occurrence(s), {u['n_lines']} ligne(s)" for u in m["unresolved"][:15]]
    L += ["", "## 2. Réseau et graphe", "",
          f"- {n['urban_lines']} lignes urbaines, {n['urban_variants']} variantes (dont {n['loop_variants']} circulaires)",
          f"- {n['suburban_groups']} groupes suburbains, {n['suburban_links']} liaisons Primus → Terminus",
          f"- Graphe : {n['nodes']} nœuds, {n['edges_declared']} arcs publiés + {n['edges_reverse_assumed']} arcs retour supposés",
          f"- Composantes faiblement connexes : {n['components']}",
          f"- Nœuds de correspondance (≥ 2 lignes) : {n['transfer_nodes']}", "",
          "| Nœud | Lignes | Passages | Degré entrant | Degré sortant | Rattachement |", "|---|---:|---:|---:|---:|---|"]
    for t in n["top_nodes_by_lines"][:15]:
        L.append(f"| {t['name']} | {t['n_lines']} | {t['n_passages']} | {t['in_degree']} | {t['out_degree']} | "
                 f"{t['match_status']} ({t['confidence']}) |")
    L += ["", "## 3. Couverture des fokontany d'Analamanga", "",
          f"- {c['n_fokontany']} fokontany ; cœur (Renivohitra + périphérie) : {c['n_core']}",
          f"- Couverture (tous) : {c['by_coverage']}", f"- Couverture (cœur) : {c['by_coverage_core']}", "",
          "| District / Arrondissement | Fokontany | Direct | Faible | Commune | Aucune | % fokontany desservis | % superficie desservie |",
          "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for d in c["by_district"]:
        L.append(f"| {d['adm2_name']} | {d['n_fokontany']} | {d['direct']} | {d['faible']} | {d['commune']} | "
                 f"{d['aucune']} | {d['pct_fokontany_direct']} | {d['pct_area_direct']} |")
    L += ["", "Plus grands fokontany sans desserte (cœur) :", ""]
    L += [f"- {u['adm4_name']} ({u['adm3_name']}) — {u['area_sqkm']:.2f} km², "
          f"{'à ' + str(int(u['rings_to_network'])) + ' voisin(s) du réseau' if u['rings_to_network'] is not None else 'éloigné du réseau'}"
          for u in c["unserved_core_largest"][:15]]
    L += ["", "_Définitions : direct = au moins un lieu rattaché au fokontany et ≥ 2 lignes ; faible = 1 seule ligne ; "
          "passage = aucun arrêt publié mais ligne traversant probablement le fokontany ; "
          "commune = rattachement seulement au niveau communal ; aucune = aucun lieu._", ""]
    return "\n".join(L)


if __name__ == "__main__":
    s = build()
    print("rattachement :", s["matching"]["by_status_places"])
    print("couverture   :", s["coverage"]["by_coverage"], "| cœur :", s["coverage"]["by_coverage_core"])
