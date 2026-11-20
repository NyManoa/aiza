"""Étape 1c — Rattachement déterministe lieux du corpus <-> fokontany (admin4) / communes (admin3).

Ordre des règles (la première qui produit un résultat l'emporte) :
  0. Table manuelle éditable (data/reference/manual_places.csv)                   -> repere_ou_variante
  Puis, pour chaque NIVEAU DE PÉRIMÈTRE exploré dans l'ordre propre au rôle du lieu :
  1. nom normalisé == nom de fokontany                                             -> exact_fokontany
     "<fokontany> <commune>" ou "<commune> <fokontany>"                            -> exact_fokontany (contexte)
  2. nom normalisé == nom de commune                                               -> commune
  3. nom = suite de mots entiers d'un nom de fokontany composé                     -> sous_chaine_fokontany
  4. nom = suite de mots entiers d'un nom de commune                               -> commune
  5. Second passage après retrait des suffixes ignorables (Nord, Sud, Hopitaly, Cite…) avec pénalité ;
     un suffixe directionnel (Nord/Sud/Est/Ouest, Avaratra/Atsimo…) devient un filtre géographique.
  6. Seul le qualificatif entre parenthèses est reconnu                            -> repere_ou_variante
  7. Sinon                                                                         -> non_resolu

Niveaux de périmètre : 1 = Antananarivo Renivohitra, 2 = périphérie (Atsimondrano, Avaradrano, Ambohidratrimo),
3 = reste d'Analamanga, 4 = régions limitrophes Itasy / Vakinankaratra (correspondances exactes uniquement).
Ordre selon le rôle : arrêt urbain [1,2] ; primus [1,2,3] ; terminus suburbain [2,3,1,4].
Homonymes départagés par : qualificatif, puis proximité du qualificatif / de la mention « passant par »,
puis chef-lieu (nom == commune), puis proximité du centre (Analakely).

Sortie : data/output/place_admin_matches.csv (+ colonnes de synthèse match_* dans places.csv)
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field

import pandas as pd

from planner import rules
from planner.core.geo import haversine_km
from planner.core.text import IGNORABLE_SUFFIXES, contains_tokens, norm, tokens
from planner.settings import get_settings

CITY_CENTER = rules.CITY_CENTER
NEIGHBOUR_REGIONS = rules.NEIGHBOUR_REGIONS
DIR_MARGIN_DEG = rules.DIR_MARGIN_DEG
ANCHOR_MAX_KM = rules.ANCHOR_MAX_KM
ANCHOR_FAR_PENALTY = rules.ANCHOR_FAR_PENALTY
DIRECTIONS = {"nord": "N", "avaratra": "N", "sud": "S", "atsimo": "S",
              "est": "E", "atsinanana": "E", "ouest": "W", "andrefana": "W"}


@dataclass
class Match:
    level: str              # "fokontany" | "commune" | "aucun"
    codes: list[str]
    status: str             # statut interne détaillé
    confidence: float
    detail: str
    n_candidates: int = 0
    tier: int | None = None


@dataclass
class Hints:
    quals: list[list[str]] = field(default_factory=list)
    anchor: tuple[float, float] | None = None
    anchor_label: str | None = None
    direction: str | None = None


class AdminIndex:
    def __init__(self) -> None:
        a4 = pd.read_csv(get_settings().tables_dir / "admin4.csv")
        a3 = pd.read_csv(get_settings().tables_dir / "admin3.csv")
        keep = {rules.ANALAMANGA, *NEIGHBOUR_REGIONS}
        self.fk = a4[a4.adm1_pcode.isin(keep)].copy()
        self.com = a3[a3.adm1_pcode.isin(keep)].copy()
        for df in (self.fk, self.com):
            df["tier"] = [self._tier(a1, a2) for a1, a2 in zip(df.adm1_pcode, df.adm2_pcode, strict=True)]
        self.fk["key"] = self.fk.adm4_name.map(norm)
        self.fk["toks"] = self.fk.key.str.split()
        self.fk["ctoks"] = self.fk.adm3_name.map(tokens)
        self.com["key"] = self.com.adm3_name.map(norm)
        self.com["toks"] = self.com.key.str.split()
        self.com["ctoks"] = self.com.toks
        for df in (self.fk, self.com):
            df["dist_center"] = [haversine_km(la, lo, *CITY_CENTER) if pd.notna(la) else 9999.0
                                 for la, lo in zip(df.lat, df.lon, strict=True)]
        self.fk_tiers = {t: g for t, g in self.fk.groupby("tier")}
        self.com_tiers = {t: g for t, g in self.com.groupby("tier")}
        self.fk_by_code = self.fk.set_index("adm4_pcode")
        self.com_by_code = self.com.set_index("adm3_pcode")
        self.fk_by_name_commune = {(k, norm(c)): p for k, c, p in zip(self.fk.key, self.fk.adm3_name, self.fk.adm4_pcode, strict=True)}
        self.com_by_name = {}
        for k, p, _tier in sorted(zip(self.com.key, self.com.adm3_pcode, self.com.tier, strict=True), key=lambda x: x[2]):
            self.com_by_name.setdefault(k, p)

    @staticmethod
    def _tier(adm1: str, adm2: str) -> int:
        if adm1 in NEIGHBOUR_REGIONS:
            return NEIGHBOUR_REGIONS[adm1]
        if adm2 in rules.TIER1_DISTRICTS:
            return 1
        if adm2 in rules.TIER2_DISTRICTS:
            return 2
        return 3

    def coord(self, m: Match) -> tuple[float, float] | None:
        if not m.codes:
            return None
        df = self.fk_by_code if m.level == "fokontany" else self.com_by_code
        r = df.loc[m.codes[0]]
        return (float(r.lat), float(r.lon)) if pd.notna(r.lat) else None


# --------------------------------------------------------------------------- filtres
def _direction_filter(df: pd.DataFrame, direction: str | None) -> pd.DataFrame:
    if df.empty or not direction:
        return df
    lat0, lon0 = CITY_CENTER
    cond = {"N": df.lat > lat0 + DIR_MARGIN_DEG, "S": df.lat < lat0 - DIR_MARGIN_DEG,
            "E": df.lon > lon0 + DIR_MARGIN_DEG, "W": df.lon < lon0 - DIR_MARGIN_DEG}[direction]
    return df[cond]


def _qualifier_filter(df: pd.DataFrame, quals: list[list[str]]) -> tuple[pd.DataFrame, bool]:
    if df.empty or not quals:
        return df, False
    mask = [any(contains_tokens(t, q) or contains_tokens(c, q) for q in quals) for t, c in zip(df.toks, df.ctoks, strict=True)]
    sub = df[mask]
    return (sub, True) if not sub.empty else (df, False)


def _order(df: pd.DataFrame, h: Hints) -> tuple[pd.DataFrame, str]:
    """Ordre déterministe des candidats : proximité de l'ancre (qualificatif/via) sinon du centre."""
    if h.anchor:
        d = [haversine_km(la, lo, *h.anchor) for la, lo in zip(df.lat, df.lon, strict=True)]
        return df.assign(_d=d).sort_values(["_d", "adm3_pcode"]), f"le plus proche de « {h.anchor_label} »"
    return df.sort_values(["dist_center", "adm3_pcode"]), "le plus proche du centre"


# --------------------------------------------------------------------------- règles
def _match_tokens(idx: AdminIndex, toks: list[str], h: Hints, tiers: list[int],
                  penalty: float = 0.0, note: str = "") -> Match | None:
    C = rules.CONFIDENCE
    key = " ".join(toks)
    for tier in tiers:
        fk = idx.fk_tiers.get(tier, idx.fk.iloc[0:0])
        com = idx.com_tiers.get(tier, idx.com.iloc[0:0])
        tnote = f" [niveau {tier}]{note}"

        # 1. fokontany exact
        exact = _direction_filter(fk[fk.key == key], h.direction)
        if not exact.empty:
            cand, by_q = _qualifier_filter(exact, h.quals)
            if len(cand) == 1:
                return Match("fokontany", list(cand.adm4_pcode), "exact_fokontany", C["exact_fokontany"] - penalty,
                             "nom identique au fokontany" + (" (qualificatif)" if by_q else "") + tnote, len(exact), tier)
            chef = cand[[t == c for t, c in zip(cand.toks, cand.ctoks, strict=True)]]
            if h.anchor or chef.empty:
                pick, rule = _order(cand, h)
            else:
                pick, rule = _order(chef, h)
                rule = "chef-lieu de commune"
            conf = C["exact_fokontany_homonyme"] - penalty
            if h.anchor and "_d" in pick and pick._d.iloc[0] > ANCHOR_MAX_KM:
                conf -= ANCHOR_FAR_PENALTY
                rule += f" (à {pick._d.iloc[0]:.1f} km : ancre éloignée, confiance réduite)"
            return Match("fokontany", [pick.adm4_pcode.iloc[0]], "exact_fokontany_homonyme",
                         conf, f"{len(cand)} homonymes, retenu : {rule}{tnote}", len(exact), tier)

        # 1b. "<fokontany> <commune>" / "<commune> <fokontany>"
        for cut in range(1, len(toks)):
            a, b = toks[:cut], toks[cut:]
            for fk_t, com_t in ((a, b), (b, a)):
                sub = fk[(fk.key == " ".join(fk_t)) & fk.ctoks.map(lambda c, ct=com_t: contains_tokens(c, ct))]
                if not sub.empty:
                    return Match("fokontany", list(sub.adm4_pcode), "exact_fokontany_contexte",
                                 C["exact_fokontany_contexte"] - penalty,
                                 f"fokontany « {' '.join(fk_t)} » de la commune « {' '.join(com_t)} »{tnote}", len(sub), tier)

        # 2. commune exacte
        cex = _direction_filter(com[com.key == key], h.direction)
        if not cex.empty:
            pick, _ = _order(cex, h)
            return Match("commune", [pick.adm3_pcode.iloc[0]], "commune", C["commune"] - penalty,
                         f"nom identique à la commune{tnote}", len(cex), tier)

        if tier == 4:   # régions limitrophes : correspondance exacte uniquement
            continue

        # 3. sous-chaîne de fokontany (mots entiers)
        sub = _direction_filter(fk[fk.toks.map(lambda t: contains_tokens(t, toks))], h.direction)
        if not sub.empty:
            sub, by_q = _qualifier_filter(sub, h.quals)
            n = len(sub)
            sub, _ = _order(sub, h)
            sub = sub.head(rules.MAX_SUBSTRING_CANDIDATES)
            conf = C["sous_chaine_fokontany"] if n <= 3 else C["sous_chaine_fokontany_large"]
            extra = f", {rules.MAX_SUBSTRING_CANDIDATES} plus proches retenus" if n > rules.MAX_SUBSTRING_CANDIDATES else ""
            return Match("fokontany", list(sub.adm4_pcode),
                         "sous_chaine_fokontany" if n <= 3 else "sous_chaine_fokontany_large", conf - penalty,
                         f"contenu dans {n} nom(s) de fokontany composé(s){extra}{tnote}", n, tier)

        # 4. sous-chaîne de commune
        csub = _direction_filter(com[com.toks.map(lambda t: contains_tokens(t, toks))], h.direction)
        if not csub.empty:
            pick, _ = _order(csub, h)
            return Match("commune", list(pick.adm3_pcode.head(3)), "commune_sous_chaine",
                         C["commune_sous_chaine"] - penalty, f"contenu dans un nom de commune{tnote}", len(csub), tier)
    return None


def tiers_for_roles(roles: set[str]) -> list[int]:
    if "arret" in roles:
        return [1, 2]
    if "primus" in roles:
        return [1, 2, 3]
    return [2, 3, 1, 4]   # terminus suburbain seul


def _manual_match(idx: AdminIndex, row: dict, roles: set[str], quals: list[str], vias: list[str],
                  manual: dict[str, dict]) -> Match:
    C = rules.CONFIDENCE
    conf = float(row.get("confidence") or C["repere_ou_variante"])
    ttype, target, note = row["target_type"].strip(), (row.get("target") or "").strip(), row.get("note", "")
    items = [x.strip() for x in target.split(";") if x.strip()]
    if ttype == "fokontany":
        codes = []
        for it in items:
            name, _, commune = it.partition("@")
            code = idx.fk_by_name_commune.get((norm(name), norm(commune)))
            if not code:
                raise ValueError(f"manual_places.csv : fokontany introuvable « {it} »")
            codes.append(code)
        return Match("fokontany", codes, "repere_ou_variante", conf, f"table manuelle : {note}", len(codes))
    if ttype == "commune":
        codes = []
        for it in items:
            code = idx.com_by_name.get(norm(it))
            if not code:
                raise ValueError(f"manual_places.csv : commune introuvable « {it} »")
            codes.append(code)
        return Match("commune", codes, "repere_ou_variante", conf, f"table manuelle : {note}", len(codes))
    if ttype == "alias":
        rest = {k: v for k, v in manual.items() if k != norm(row["place"])}  # pas de boucle d'alias
        inner = match_place(idx, target, quals, vias, roles, rest)
        if inner.level != "aucun":
            return Match(inner.level, inner.codes, "repere_ou_variante", min(conf, inner.confidence),
                         f"table manuelle : {note} -> « {target} » ({inner.detail})", inner.n_candidates, inner.tier)
        return Match("aucun", [], "non_resolu", 0.0, f"table manuelle : alias « {target} » non reconnu")
    return Match("aucun", [], "non_resolu", 0.0, f"table manuelle : {note}")


def match_place(idx: AdminIndex, name: str, qualifiers: list[str], vias: list[str],
                roles: set[str], manual: dict[str, dict]) -> Match:
    C = rules.CONFIDENCE
    key = norm(name)
    if key in manual:
        return _manual_match(idx, manual[key], roles, qualifiers, vias, manual)

    tiers = tiers_for_roles(roles)
    h = Hints(quals=[tokens(q) for q in qualifiers if q])
    # Ancre géographique : qualificatif puis mention « passant par » (sert à départager des homonymes).
    for label in [*qualifiers, *vias]:
        am = _match_tokens(idx, tokens(label), Hints(), [1, 2, 3])
        if am and (c := idx.coord(am)):
            h.anchor, h.anchor_label = c, label
            break

    toks = key.split()
    if r := _match_tokens(idx, toks, h, tiers):
        return r
    stripped = [t for t in toks if t not in IGNORABLE_SUFFIXES]
    if stripped and stripped != toks:
        removed = [t for t in toks if t in IGNORABLE_SUFFIXES]
        dirs = {DIRECTIONS[t] for t in removed if t in DIRECTIONS}
        h2 = Hints(h.quals, h.anchor, h.anchor_label, dirs.pop() if len(dirs) == 1 else None)
        dnote = f", filtre géographique {h2.direction}" if h2.direction else ""
        if r := _match_tokens(idx, stripped, h2, tiers, rules.SUFFIX_PENALTY,
                              f" (suffixe « {' '.join(removed)} » ignoré{dnote})"):
            return r
    for q in h.quals:
        if r := _match_tokens(idx, q, Hints(), tiers):
            return Match(r.level, r.codes, "qualificatif_seul", min(r.confidence, C["qualificatif_seul"]),
                         f"seul le qualificatif « {' '.join(q)} » est reconnu ({r.detail})", r.n_candidates, r.tier)
    return Match("aucun", [], "non_resolu", 0.0, "aucune règle applicable — à compléter dans manual_places.csv")


def load_manual() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if get_settings().manual_places_csv.exists():
        with open(get_settings().manual_places_csv, encoding="utf-8") as fh:
            for row in csv.DictReader(r for r in fh if r.strip() and not r.lstrip().startswith("#")):
                out[norm(row["place"])] = row
    return out


def public_status(m: Match) -> str:
    """Ramène le statut interne aux 5 catégories publiques."""
    if m.status in ("repere_ou_variante", "qualificatif_seul"):
        return "repere_ou_variante"
    if m.level == "commune":
        return "commune"
    if m.status.startswith("exact_fokontany"):
        return "exact_fokontany"
    if m.status.startswith("sous_chaine"):
        return "sous_chaine_fokontany"
    return "non_resolu"


def _split(v) -> list[str]:
    return [x.strip() for x in str(v).split("|") if x.strip()] if pd.notna(v) else []


def _match_coord(idx: AdminIndex, m: Match) -> tuple[float, float] | None:
    df = idx.fk_by_code if m.level == "fokontany" else idx.com_by_code
    pts = [(df.loc[c].lat, df.loc[c].lon) for c in m.codes if c in df.index and pd.notna(df.loc[c].lat)]
    if not pts:
        return None
    return (sum(a for a, _ in pts) / len(pts), sum(b for _, b in pts) / len(pts))


def route_neighbors() -> dict[str, set[str]]:
    """Lieux adjacents dans les trajets urbains publiés (arrêt précédent / suivant)."""
    steps = pd.read_csv(get_settings().tables_dir / "route_steps.csv")
    nb: dict[str, set[str]] = {}
    for _, g in steps.groupby("variant_id"):
        by_seq = [list(gg.place_id) for _, gg in g.groupby("seq", sort=True)]
        for a, b in zip(by_seq, by_seq[1:], strict=False):
            for x in a:
                for y in b:
                    if x != y:
                        nb.setdefault(x, set()).add(y)
                        nb.setdefault(y, set()).add(x)
    return nb


def apply_route_consistency(idx: AdminIndex, name: str, roles: set[str], m: Match,
                            anchor: tuple[float, float], anchor_label: str) -> Match:
    """Règle de cohérence d'itinéraire (déterministe) : voir rules.ROUTE_CONSISTENCY_KM."""
    if m.level != "fokontany" or m.status in ("repere_ou_variante", "qualificatif_seul") or not m.codes:
        return m
    lim = rules.ROUTE_CONSISTENCY_KM
    fk = idx.fk_by_code
    d_cur = min(haversine_km(fk.loc[c].lat, fk.loc[c].lon, *anchor) for c in m.codes)
    if d_cur <= lim:
        return m
    toks = norm(name).split()
    stripped = [t for t in toks if t not in IGNORABLE_SUFFIXES] or toks
    tiers = tiers_for_roles(roles)
    cand = idx.fk[idx.fk.tier.isin(tiers) & idx.fk.toks.map(lambda t: contains_tokens(t, stripped))].copy()
    if cand.empty:
        return m
    cand["_d"] = [haversine_km(a, b, *anchor) for a, b in zip(cand.lat, cand.lon, strict=True)]
    near = cand[cand._d <= lim].sort_values(["_d", "adm4_pcode"]).head(3)
    if near.empty or near._d.iloc[0] >= d_cur / 2:
        return m
    exact = all(k == " ".join(stripped) for k in near.key)
    rule = "exact_fokontany_homonyme" if exact else ("sous_chaine_fokontany" if len(near) <= 3 else "sous_chaine_fokontany_large")
    return Match("fokontany", list(near.adm4_pcode), rule,
                 rules.CONFIDENCE[rule] - rules.ROUTE_CONSISTENCY_PENALTY,
                 f"cohérence avec les arrêts voisins ({anchor_label}) : candidat à {near._d.iloc[0]:.1f} km retenu "
                 f"au lieu de {d_cur:.1f} km [{m.detail}]", m.n_candidates, m.tier)


def build() -> dict[str, int]:
    idx = AdminIndex()
    manual = load_manual()
    places = pd.read_csv(get_settings().tables_dir / "places.csv")
    places = places.drop(columns=[c for c in places.columns if c.startswith("match_") or c == "n_matches"])
    # Passe 1 : règles lexicales.
    first: dict[str, Match] = {}
    for p in places.itertuples():
        first[p.place_id] = match_place(idx, p.display_name, _split(p.qualifiers), _split(p.vias), set(_split(p.roles)), manual)
    # Passe 2 : cohérence avec les arrêts voisins (lieux non saisis dans la table manuelle).
    coords = {pid: c for pid, m in first.items() if (c := _match_coord(idx, m))}
    nbrs = route_neighbors()
    names = dict(zip(places.place_id, places.display_name, strict=True))
    rows, summary = [], []
    n_consistency = 0
    for p in places.itertuples():
        roles = set(_split(p.roles))
        m = first[p.place_id]
        pts = [(n, coords[n]) for n in sorted(nbrs.get(p.place_id, ())) if n in coords]
        if pts and norm(p.display_name) not in manual:
            anchor = (sum(c[0] for _, c in pts) / len(pts), sum(c[1] for _, c in pts) / len(pts))
            m2 = apply_route_consistency(idx, p.display_name, roles, m, anchor, ", ".join(names[n] for n, _ in pts[:3]))
            n_consistency += m2 is not m
            m = m2
        status = public_status(m)
        summary.append({"place_id": p.place_id, "match_status": status, "match_rule": m.status,
                        "match_level": m.level, "match_confidence": round(m.confidence, 3),
                        "match_detail": m.detail, "n_matches": len(m.codes)})
        base = {"place_id": p.place_id, "status": status, "rule": m.status,
                "confidence": round(m.confidence, 3), "detail": m.detail, "n_candidates": m.n_candidates}
        for rank, code in enumerate(m.codes, start=1):
            if m.level == "fokontany":
                r = idx.fk_by_code.loc[code]
                rows.append({**base, "rank": rank, "level": "fokontany", "adm4_pcode": code, "adm4_name": r.adm4_name,
                             "adm3_pcode": r.adm3_pcode, "adm3_name": r.adm3_name, "adm2_pcode": r.adm2_pcode,
                             "adm2_name": r.adm2_name, "adm1_pcode": r.adm1_pcode})
            else:
                r = idx.com_by_code.loc[code]
                rows.append({**base, "rank": rank, "level": "commune", "adm4_pcode": None, "adm4_name": None,
                             "adm3_pcode": code, "adm3_name": r.adm3_name, "adm2_pcode": r.adm2_pcode,
                             "adm2_name": r.adm2_name, "adm1_pcode": r.adm1_pcode})
        if not m.codes:
            rows.append({**base, "rank": 0, "level": "aucun"})
    pd.DataFrame(rows).to_csv(get_settings().tables_dir / "place_admin_matches.csv", index=False)
    places = places.merge(pd.DataFrame(summary), on="place_id")
    places.to_csv(get_settings().tables_dir / "places.csv", index=False)
    counts = places.match_status.value_counts().to_dict()
    counts["lieux"] = len(places)
    counts["corriges_coherence_itineraire"] = n_consistency
    return counts


if __name__ == "__main__":
    for k, v in build().items():
        print(f"{k:24s} {v}")
