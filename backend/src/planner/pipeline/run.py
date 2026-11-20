"""Orchestration reproductible du pipeline.

  python -m planner.pipeline           # reconstruit data/processed/
"""
from __future__ import annotations

import logging
import time
from collections.abc import Callable

from planner.pipeline import admin, analysis, bus_parser, geometry, graph, matching
from planner.settings import get_settings

log = logging.getLogger("planner.pipeline")

STEPS: list[tuple[str, Callable[[], dict]]] = [
    ("1a référentiel administratif", admin.build),
    ("1b parsing du corpus de transport", bus_parser.build),
    ("1c rattachement lieux <-> fokontany", matching.build),
    ("1d géométrie et fokontany traversés", geometry.build),
    ("2a graphe de transport", graph.build),
]


def run() -> dict:
    s = get_settings()
    for d in (s.tables_dir, s.graph_dir, s.analysis_dir):
        d.mkdir(parents=True, exist_ok=True)
    summary: dict[str, dict] = {}
    for label, fn in STEPS:
        t = time.perf_counter()
        summary[label] = fn()
        log.info("[%s] %.1fs %s", label, time.perf_counter() - t, summary[label])
    t = time.perf_counter()
    stats = analysis.build()
    summary["2b statistiques & couverture"] = {
        "rattachement": stats["matching"]["by_status_places"],
        "couverture_coeur": stats["coverage"]["by_coverage_core"],
    }
    log.info("[2b statistiques & couverture] %.1fs", time.perf_counter() - t)
    return summary


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for step, res in run().items():
        print(f"[{step}]")
        for k, v in res.items():
            print(f"    {k:28s} {v}")
    print(f"Sorties : {get_settings().processed_dir}")


if __name__ == "__main__":
    main()
