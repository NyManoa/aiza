"""Planificateur d'itinéraires : énumération exhaustive bornée (0, 1, 2 correspondances), élimination des trajets
inutiles, classement par score explicite.

Hypothèses explicites :
  - variante non circulaire : sens retour supposé (signalé, pénalisé) ;
  - variante circulaire (départ == arrivée) : sens publié uniquement ;
  - liaison suburbaine : montée/descente au Primus ou au Terminus (ou à un fokontany traversé DÉCLARÉ) ;
  - fokontany traversé (position virtuelle) : montée/descente possible mais signalée, jamais de correspondance.
Distances : vol d'oiseau entre arrêts consécutifs (ordre de grandeur, pas kilométrage routier).

Élimination (dans cet ordre, toutes déterministes) :
  1. doublons      : même suite de lignes -> on garde la meilleure variante (points de correspondance compris) ;
  2. dominés       : un trajet à k correspondances dont les lignes contiennent celles d'un trajet plus simple ;
  3. va-et-vient   : un trajet qui repasse par un même lieu, s'il existe une alternative sans va-et-vient avec
                     au plus autant de correspondances ;
  4. détours       : un trajet dont la distance dépasse rules.MAX_DETOUR_RATIO × la distance directe (et
                     + rules.MAX_DETOUR_EXTRA_KM), s'il existe une alternative raisonnable avec au plus autant de
                     correspondances.
"""
from __future__ import annotations

import heapq
from collections import Counter, defaultdict
from functools import cached_property

from planner import rules
from planner.engine.models import Ride
from planner.engine.repository import NetworkRepository, is_virtual

Transfer = tuple[str, str, str]  # (lieu d'arrivée, lieu de reprise, type)
WALK_MODES = ("repli_a_pied", "proche_a_pied", "approche_a_pied")


def walk_penalty(km: float) -> tuple[float, float]:
    """(pénalité jusqu'au seuil, pénalité au-delà du seuil) pour une distance de marche."""
    near = min(km, rules.FALLBACK_MAX_KM)
    return rules.W_WALK_KM * near, rules.W_WALK_FAR_KM * max(0.0, km - rules.FALLBACK_MAX_KM)


def score_itinerary(*, n_transfers: int, n_walk_transfers: int, n_walk_ends: int, walk_km: float, bus_km: float,
                    n_unknown_km: int, conf_min: float, n_reverse: int, n_wrap: int, n_revisits: int,
                    n_stops: int) -> dict[str, float]:
    """Décomposition du score : chaque terme est une règle explicite de `planner.rules`."""
    return {
        "base": rules.SCORE_BASE,
        "correspondances": -rules.W_TRANSFER * n_transfers,
        "correspondances_a_pied": -rules.W_WALK_TRANSFER * n_walk_transfers,
        "acces_a_pied": -rules.W_WALK_ACCESS * n_walk_ends,
        "distance_a_pied": -walk_penalty(walk_km)[0],
        "marche_au_dela_du_seuil": -walk_penalty(walk_km)[1],
        "distance_en_bus": -rules.W_BUS_KM * bus_km,
        "distance_inconnue": -rules.W_UNKNOWN_KM * n_unknown_km,
        "confiance_rattachement": -rules.W_CONFIDENCE * (1 - conf_min),
        "sens_retour_suppose": -rules.W_REVERSE * n_reverse,
        "passage_terminus_boucle": -rules.W_WRAP * n_wrap,
        "va_et_vient": -rules.W_REVISIT * n_revisits,
        "arrets_intermediaires": -rules.W_STOP * n_stops,
    }


class ItineraryPlanner:
    def __init__(self, repo: NetworkRepository) -> None:
        self.repo = repo
        # nombre cumulé de positions réelles : real_cum[si][k] = nb de positions réelles dans [0, k]
        self.real_cum: list[list[int]] = []
        for pos in repo.positions:
            acc, c = [], 0
            for p in pos:
                c += p.real
                acc.append(c)
            self.real_cum.append(acc)

    # ------------------------------------------------------------------ index des courses
    def _real_between(self, si: int, a: int, b: int) -> int:
        """Positions réelles strictement entre a et b (a < b)."""
        if b - a <= 1:
            return 0
        rc = self.real_cum[si]
        return rc[b - 1] - rc[a]

    @cached_property
    def reach(self) -> dict[str, dict[str, list[Ride]]]:
        """reach[a][b] = meilleure course par service pour aller de a à b sans correspondance."""
        repo = self.repo
        out: dict[str, dict[str, dict[int, Ride]]] = defaultdict(lambda: defaultdict(dict))
        for si, s in enumerate(repo.services):
            P = repo.positions[si]
            n, loop = len(P), s["loop"]
            for i in range(n):
                for j in range(n):
                    if i == j:
                        continue
                    if loop:
                        if i == n - 1:      # dernière position == première : montée au départ
                            continue
                        if j > i:
                            rev, wrap = False, False
                            km, unk = P[j].km - P[i].km, P[j].unknown - P[i].unknown
                            stops = self._real_between(si, i, j)
                        elif j == 0:
                            continue
                        else:
                            rev, wrap = False, True
                            km = (P[n - 1].km - P[i].km) + P[j].km
                            unk = (P[n - 1].unknown - P[i].unknown) + P[j].unknown
                            stops = self._real_between(si, i, n - 1) + 1 + self._real_between(si, 0, j)
                    else:
                        lo, hi = min(i, j), max(i, j)
                        rev, wrap = j < i, False
                        km, unk = P[hi].km - P[lo].km, P[hi].unknown - P[lo].unknown
                        stops = self._real_between(si, lo, hi)
                    for a in P[i].places:
                        for b in P[j].places:
                            if a == b:
                                continue
                            r = Ride(si, i, j, a, b, rev, wrap, round(km, 4), unk, stops)
                            cur = out[a][b].get(si)
                            if cur is None or r.cost_key() < cur.cost_key():
                                out[a][b][si] = r
        res: dict[str, dict[str, list[Ride]]] = {}
        for a, m in out.items():
            res[a] = {}
            for b, d in m.items():
                best: dict[str, Ride] = {}
                for r in sorted(d.values(), key=lambda r: (r.cost_key(), repo.services[r.service]["id"])):
                    best.setdefault(repo.services[r.service]["line_id"], r)
                res[a][b] = list(best.values())
        return res

    def warm_up(self) -> None:
        _ = self.reach

    def _line(self, r: Ride) -> str:
        return self.repo.services[r.service]["line_id"]

    @staticmethod
    def _best_per_line(rides: list[Ride]) -> list[Ride]:
        return rides  # reach ne contient déjà qu'une course (la meilleure) par ligne

    def _transfer_points(self, place: str) -> list[tuple[str, str]]:
        return [(place, "meme_lieu")] + [(w, "a_pied_meme_fokontany") for w in sorted(self.repo.walk.get(place, ()))]

    def _traversal(self, r: Ride) -> list[int]:
        n = len(self.repo.positions[r.service])
        if r.wrap:
            return list(range(r.i, n)) + list(range(1, r.j + 1))
        step = -1 if r.j < r.i else 1
        return list(range(r.i, r.j + step, step))

    # ------------------------------------------------------------------ recherche
    def plan(self, origin_access: dict[str, dict], dest_access: dict[str, dict],
             max_transfers: int = rules.MAX_TRANSFERS, direct_km: float | None = None) -> dict:
        orig_acc, dest_acc = origin_access, dest_access
        reach = self.reach
        found: dict[tuple, dict] = {}
        n_dupes = [0]

        def add(legs: list[Ride], transfers: list[Transfer]) -> None:
            lines = tuple(self._line(r) for r in legs)
            if len(set(lines)) != len(lines):
                return
            m = self._metrics(legs, transfers, orig_acc[legs[0].src], dest_acc[legs[-1].dst], direct_km)
            # Une seule option par suite de lignes (élimination des doublons dès l'énumération).
            cur = found.get(lines)
            if cur is None or (m["score"], -m["total_km"]) > (cur["score"], -cur["total_km"]):
                if cur is not None:
                    n_dupes[0] += 1
                found[lines] = m
            else:
                n_dupes[0] += 1

        dest_set = set(dest_acc)
        for a in sorted(orig_acc):                                     # 0 correspondance
            for b in sorted(dest_set & set(reach.get(a, {}))):
                for r in self._best_per_line(reach[a][b]):
                    add([r], [])
        if max_transfers >= 1:                                         # 1 correspondance
            for a in sorted(orig_acc):
                for x, r1s in reach.get(a, {}).items():
                    if x in dest_set or is_virtual(x):
                        continue
                    for t, tt in self._transfer_points(x):
                        for b in dest_set & set(reach.get(t, {})):
                            if t == b:
                                continue
                            for r1 in self._best_per_line(r1s):
                                for r2 in self._best_per_line(reach[t][b]):
                                    add([r1, r2], [(x, t, tt)])
        if max_transfers >= 2:                                         # 2 correspondances
            pre: dict[str, set[str]] = defaultdict(set)
            for y, m in reach.items():
                if is_virtual(y):
                    continue
                for b in dest_set & set(m):
                    if y != b:
                        pre[y].add(b)
            for a in sorted(orig_acc):
                for x, r1s in reach.get(a, {}).items():
                    if x in dest_set or x in orig_acc or is_virtual(x):
                        continue
                    for t1, tt1 in self._transfer_points(x):
                        for y, r2s in reach.get(t1, {}).items():
                            if y in dest_set or y in orig_acc or y == x or is_virtual(y):
                                continue
                            for t2, tt2 in self._transfer_points(y):
                                for b in pre.get(t2, ()):
                                    for r1 in self._best_per_line(r1s):
                                        for r2 in self._best_per_line(r2s):
                                            for r3 in self._best_per_line(reach[t2][b]):
                                                add([r1, r2, r3], [(x, t1, tt1), (y, t2, tt2)])

        itins, pruned = self._prune(list(found.values()))
        pruned["doublons"] = n_dupes[0]
        key = lambda it: (-it["score"], it["transfers"], it["signature"])  # noqa: E731
        itins.sort(key=key)
        by_k: dict[int, list[dict]] = defaultdict(list)
        for it in itins:
            by_k[it["transfers"]].append(it)
        counts = {str(k): len(v) for k, v in sorted(by_k.items())}
        kept = [it for k in sorted(by_k) for it in by_k[k][: rules.MAX_RESULTS_PER_CATEGORY]]
        kept.sort(key=key)
        kept = [self._render(m) for m in kept]
        for n, it in enumerate(kept, start=1):
            it["id"] = n
        return {"itineraries": kept, "counts": counts, "pruned": pruned, "highlights": self._highlights(kept)}

    # ------------------------------------------------------------------ palier « approche »
    def _ride_cost(self, r: Ride) -> float:
        return (rules.W_BUS_KM * r.km + rules.W_REVERSE * r.reverse + rules.W_WRAP * r.wrap
                + rules.W_UNKNOWN_KM * r.km_unknown + rules.W_STOP * r.n_stops)

    def approach(self, origin_access: dict[str, dict], dest_access: dict[str, dict],
                 direct_km: float | None = None, max_legs: int = rules.APPROACH_MAX_LEGS) -> dict:
        """Plus court chemin pondéré (Dijkstra) sur les états (lieu, nb de tronçons), sans limite à 2 correspondances.

        Coût = mêmes poids explicites que le score : accès, km en bus, correspondances, marche finale jusqu'à
        l'arrivée. Utilisé seulement en dernier recours, quand l'énumération exhaustive (≤ 2 correspondances) ne
        trouve rien : garantit un itinéraire cohérent (« prendre des bus vers les fokontany les plus proches »).
        """
        reach = self.reach
        start_cost = lambda a: rules.W_WALK_KM * a["walk_km"] + rules.W_CONFIDENCE * (1 - a["confidence"])  # noqa: E731
        # état : (lieu, n_legs) ; prev[état] = (état précédent, course | None si correspondance à pied)
        best: dict[tuple[str, int], float] = {}
        prev: dict[tuple[str, int], tuple[tuple[str, int] | None, Ride | None, str | None]] = {}
        pq: list[tuple[float, str, int]] = []
        for pid in sorted(origin_access):
            c = start_cost(origin_access[pid])
            best[(pid, 0)] = c
            prev[(pid, 0)] = (None, None, None)
            heapq.heappush(pq, (c, pid, 0))
        while pq:
            c, x, n = heapq.heappop(pq)
            if c > best.get((x, n), float("inf")) or n >= max_legs:
                continue
            if n > 0 and is_virtual(x):
                continue                                   # pas de correspondance en passage
            sources = [(x, None)] + ([(w, "a_pied_meme_fokontany") for w in sorted(self.repo.walk.get(x, ()))] if n else [])
            for src, ttype in sources:
                extra = (rules.W_TRANSFER if n else 0.0) + (rules.W_WALK_TRANSFER + rules.W_WALK_KM * self.repo.walk_km(x, src)
                                                            if ttype else 0.0)
                for y, rides in reach.get(src, {}).items():
                    for r in rides:
                        nc = c + extra + self._ride_cost(r)
                        key = (y, n + 1)
                        if nc < best.get(key, float("inf")) - 1e-9:
                            best[key] = nc
                            prev[key] = ((x, n), r, ttype)
                            heapq.heappush(pq, (nc, y, n + 1))
        ends = []
        for (y, n), c in best.items():
            if n > 0 and y in dest_access:
                a = dest_access[y]
                ends.append((c + sum(walk_penalty(a["walk_km"])) + rules.W_CONFIDENCE * (1 - a["confidence"]), y, n))
        ends.sort()
        found: dict[tuple, dict] = {}
        for _, y, n in ends:
            legs, transfers, state = [], [], (y, n)
            while prev[state][0] is not None:
                p_state, ride, ttype = prev[state]
                legs.append(ride)
                if p_state[1] > 0:
                    transfers.append((p_state[0], ride.src, ttype or "meme_lieu"))
                state = p_state
            legs.reverse()
            transfers.reverse()
            lines = tuple(self._line(r) for r in legs)
            if lines in found or len(set(lines)) != len(lines):
                continue
            found[lines] = self._metrics(legs, transfers, origin_access[legs[0].src], dest_access[y], direct_km)
            if len(found) >= rules.APPROACH_RESULTS:
                break
        itins = sorted(found.values(), key=lambda it: (-it["score"], it["transfers"], it["signature"]))
        itins = [self._render(m) for m in itins]
        for i, it in enumerate(itins, start=1):
            it["id"] = i
        counts: dict[str, int] = defaultdict(int)
        for it in itins:
            counts[str(it["transfers"])] += 1
        return {"itineraries": itins, "counts": dict(counts), "pruned": {"doublons": 0, "domines": 0, "va_et_vient": 0,
                "detours": 0}, "highlights": self._highlights(itins)}

    # ------------------------------------------------------------------ élimination
    @staticmethod
    def _prune(itins: list[dict]) -> tuple[list[dict], dict[str, int]]:
        stats = {"doublons": 0, "domines": 0, "va_et_vient": 0, "detours": 0}
        # 1. doublons : traités pendant l'énumération (une option par suite de lignes)
        # 2. dominés par un sous-ensemble de lignes avec moins de correspondances
        by_k: dict[int, list[frozenset]] = defaultdict(list)
        for it in itins:
            by_k[it["transfers"]].append(frozenset(it["line_ids"]))
        kept = [it for it in itins
                if not any(prev <= frozenset(it["line_ids"]) for k in range(it["transfers"]) for prev in by_k[k])]
        stats["domines"] = len(itins) - len(kept)
        itins = kept

        # 3-4. va-et-vient et détours, s'il existe une alternative propre avec au plus autant de correspondances
        def clean(it: dict) -> bool:
            return it["revisits"] == 0 and not it["is_detour"]

        min_clean_k = min((it["transfers"] for it in itins if clean(it)), default=None)
        min_norevisit_k = min((it["transfers"] for it in itins if it["revisits"] == 0), default=None)
        out = []
        for it in itins:
            if it["revisits"] and min_norevisit_k is not None and min_norevisit_k <= it["transfers"]:
                stats["va_et_vient"] += 1
                continue
            if it["is_detour"] and min_clean_k is not None and min_clean_k <= it["transfers"]:
                stats["detours"] += 1
                continue
            out.append(it)
        return out, stats

    @staticmethod
    def _highlights(itins: list[dict]) -> dict[str, int | None]:
        if not itins:
            return {"recommande": None, "plus_court": None, "moins_de_marche": None, "moins_de_correspondances": None}
        pick = lambda key: min(itins, key=key)["id"]  # noqa: E731
        return {
            "recommande": itins[0]["id"],
            "plus_court": pick(lambda it: (it["total_km"], -it["score"])),
            "moins_de_marche": pick(lambda it: (it["walk_km"], -it["score"])),
            "moins_de_correspondances": pick(lambda it: (it["transfers"], -it["score"])),
        }

    # ------------------------------------------------------------------ construction
    def _metrics(self, legs: list[Ride], transfers: list[Transfer], oacc: dict, dacc: dict,
                 direct_km: float | None) -> dict:
        """Métriques et score (léger : appelé pour chaque combinaison énumérée)."""
        repo = self.repo
        conf_min = min(oacc["confidence"], dacc["confidence"])
        walk_tr = [repo.walk_km(x, t) for x, t, tt in transfers if tt != "meme_lieu"]
        walk_km = round(oacc["walk_km"] + dacc["walk_km"] + sum(walk_tr), 3)
        bus_km = round(sum(r.km for r in legs), 3)
        total_km = round(bus_km + walk_km, 3)
        tokens: list[tuple[str, ...]] = []
        for r in legs:
            P = repo.positions[r.service]
            for k in self._traversal(r):
                if P[k].real and (not tokens or tokens[-1] != P[k].places):
                    tokens.append(P[k].places)
        revisits = sum(c - 1 for c in Counter(tokens).values() if c > 1)
        ref = max(direct_km or 0.0, 0.5)
        is_detour = (direct_km is not None and total_km > rules.MAX_DETOUR_RATIO * ref
                     and total_km > ref + rules.MAX_DETOUR_EXTRA_KM)
        breakdown = score_itinerary(
            n_transfers=len(transfers), n_walk_transfers=len(walk_tr),
            n_walk_ends=sum(a["mode"] in WALK_MODES for a in (oacc, dacc)), walk_km=walk_km, bus_km=bus_km,
            n_unknown_km=sum(r.km_unknown for r in legs), conf_min=conf_min, n_reverse=sum(r.reverse for r in legs),
            n_wrap=sum(r.wrap for r in legs), n_revisits=revisits,
            n_stops=sum(r.n_stops for r in legs if repo.services[r.service]["stops_known"]))
        return {
            "_legs": legs, "_transfers": transfers,
            "transfers": len(transfers), "score": round(sum(breakdown.values()), 2),
            "score_breakdown": {k: round(v, 2) for k, v in breakdown.items()},
            "line_ids": [self._line(r) for r in legs],
            "confidence_min": round(conf_min, 3), "statuses": sorted({oacc["status"], dacc["status"]}),
            "access": {"origin": oacc, "destination": dacc},
            "bus_km": bus_km, "walk_km": walk_km, "total_km": total_km,
            "direct_km": round(direct_km, 2) if direct_km is not None else None,
            "detour_ratio": round(total_km / ref, 2) if direct_km is not None else None,
            "is_detour": is_detour, "revisits": revisits,
            "has_reverse": any(r.reverse for r in legs), "has_walk": walk_km > 0 or bool(walk_tr),
            "has_passage": is_virtual(legs[0].src) or is_virtual(legs[-1].dst),
            "signature": " > ".join(f"{repo.services[r.service]['line_code']}:{r.src}-{r.dst}" for r in legs),
        }

    def _render(self, m: dict) -> dict:
        """Itinéraire détaillé (appelé uniquement pour les itinéraires retenus)."""
        repo = self.repo
        legs, transfers = m.pop("_legs"), m.pop("_transfers")
        out_legs = []
        for r in legs:
            s = repo.services[r.service]
            P = repo.positions[r.service]
            trav = self._traversal(r)
            real = [k for k in trav if P[k].real]
            out_legs.append({
                "service_id": s["id"], "line_id": s["line_id"], "line_code": s["line_code"], "zone": s["zone"],
                "variant": s["label"], "sector": s["sector"], "color": s["color"], "note": s["note"],
                "loop": s["loop"], "from": repo.place_summary(r.src), "to": repo.place_summary(r.dst),
                "direction": "retour_suppose" if r.reverse else "aller", "wrap": r.wrap,
                "n_segments": (len(real) - 1 if s["stops_known"] else None),
                "stops": [repo.position_label(r.service, k) for k in real] if s["stops_known"] else [],
                "passages": [repo.places[P[k].places[0]]["name"].removesuffix(" (passage)") for k in trav if not P[k].real],
                "km": round(r.km, 2), "km_unknown": r.km_unknown,
                # Direction affichée : terminus dans le sens de circulation (une boucle revient à son départ).
                "headsign": repo.stop_label(s, 0 if r.reverse else -1),
                "stops_known": s["stops_known"], "via_mention": s["via_mention"], "raw": s["raw"],
            })
        m["legs"] = out_legs
        m["zones"] = sorted({leg["zone"] for leg in out_legs})
        m["transfer_points"] = [
            {"at": repo.place_summary(x), "to": repo.place_summary(t), "type": tt,
             "fokontany": repo.walk_fk.get((x, t)) if tt != "meme_lieu" else None,
             "walk_km": repo.walk_km(x, t) if tt != "meme_lieu" else 0.0}
            for x, t, tt in transfers]
        m["signature"] = " > ".join(f"{leg['line_code']}:{leg['from']['name']}-{leg['to']['name']}" for leg in out_legs)
        m["id"] = 0
        return m
