"""Ligne de commande.

  planner pipeline                         reconstruire data/processed/
  planner serve [--port 8000] [--reload]   lancer l'API
  planner search "Itaosy"
  planner route MG11118001001 MG11117110001 [--max 2] [--top 10]
"""
from __future__ import annotations

import argparse


def main() -> None:
    ap = argparse.ArgumentParser(prog="planner")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("pipeline")
    sv = sub.add_parser("serve")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8000)
    sv.add_argument("--reload", action="store_true")
    s = sub.add_parser("search")
    s.add_argument("q")
    r = sub.add_parser("route")
    r.add_argument("origin")
    r.add_argument("destination")
    r.add_argument("--max", type=int, default=2)
    r.add_argument("--top", type=int, default=10)
    a = ap.parse_args()

    if a.cmd == "pipeline":
        from planner.pipeline.run import main as run
        return run()
    if a.cmd == "serve":
        import uvicorn
        return uvicorn.run("planner.api.app:app", host=a.host, port=a.port, reload=a.reload)

    from planner.engine import TransportService
    from planner.settings import get_settings
    svc = TransportService.from_settings(get_settings())
    if a.cmd == "search":
        for it in svc.search(a.q):
            print(f"{it['adm4_pcode']}  {it['adm4_name']:35s} {it['adm3_name']:25s} {it['adm1_name']:15s} "
                  f"desserte={it['served']['coverage']} lignes={it['served']['n_lines']}")
        return
    res = svc.plan(a.origin, a.destination, a.max)
    for end in ("origin", "destination"):
        e = res[end]
        print(f"[{end}] {e['fokontany']['adm4_name']} ({e['fokontany']['adm3_name']}) — {e['served']['coverage']}")
        for w in e["warnings"]:
            print("   !", w)
        for f in e["fallback"]:
            print(f"   -> repli : {f['adm4_name']} ({f['relation']}, {f['distance_km']} km)")
    for m in res["messages"]:
        print("*", m)
    print("Itinéraires par nombre de correspondances :", res["counts"])
    for it in res["itineraries"][: a.top]:
        print(f"\n#{it['id']}  score {it['score']}  ({it['transfers']} corresp.)  confiance min {it['confidence_min']}")
        for leg in it["legs"]:
            arrow = "<-" if leg["direction"] == "retour_suppose" else "->"
            extra = f" [{leg['variant']}]" if leg["variant"] != "Unique" else ""
            print(f"   {leg['line_code']}{extra}: {leg['from']['name']} {arrow} {leg['to']['name']}"
                  + ("" if leg["stops_known"] else "  (arrêts intermédiaires non fournis)"))


if __name__ == "__main__":
    main()
