"""Recherche de fokontany par nom normalisé, pcode ou nom d'arrêt du réseau."""
from __future__ import annotations

from planner import rules
from planner.core.text import norm
from planner.engine.repository import NetworkRepository


class SearchService:
    def __init__(self, repo: NetworkRepository) -> None:
        self.repo = repo

    def _item(self, code: str, how: str, via_place: str | None = None) -> dict:
        item = self.repo.admin_label(code)
        item.update(match=how, via_place=via_place, served=self.repo.served_summary(code))
        return item

    def search(self, q: str, limit: int = 20) -> list[dict]:
        """Ordre : pcode > fokontany d'Analamanga au nom exact > arrêts du réseau > autres fokontany
        (nom exact, puis début de nom, puis sous-chaîne ; Analamanga et desservis d'abord)."""
        repo = self.repo
        q = q.strip()
        if not q:
            return []
        out: list[dict] = []
        seen: set[str] = set()

        def push(code: str, how: str, via: str | None = None) -> None:
            if code not in seen:
                seen.add(code)
                out.append(self._item(code, how, via))

        if q.upper().startswith("MG"):
            for code in sorted(repo.fokontany):
                if code.startswith(q.upper()):
                    push(code, "pcode")
                    if len(out) >= limit:
                        return out
        nq = norm(q)
        if not nq:
            return out[:limit]
        for code, f in sorted(repo.fokontany.items()):
            if f["_key"] == nq and f["adm1_pcode"] == rules.ANALAMANGA:
                push(code, "nom")
        for _pid, p in sorted(repo.places.items(), key=lambda kv: (norm(kv[1]["name"]) != nq, kv[0])):
            if nq in norm(p["name"]):
                for code in [c for c in (p["fokontany"] or "").split(";") if c][:3]:
                    push(code, "arret", p["name"])
        cands = []
        for code, f in repo.fokontany.items():
            k = f["_key"]
            if nq in k and code not in seen:
                rank = 0 if k == nq else (1 if k.startswith(nq) else 2)
                cands.append((rank, f["adm1_pcode"] != rules.ANALAMANGA, code not in repo.served, k, code))
        cands.sort()
        for c in cands[: limit * 2]:
            push(c[-1], "nom")
        return out[:limit]
