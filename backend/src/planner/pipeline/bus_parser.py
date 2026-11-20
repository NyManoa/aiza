"""Étape 1b — Parsing structuré de liste_bus_antananarivo.txt.

Produit (data/output/) :
  lines.csv           une ligne par ligne de transport (58 urbaines + groupes suburbains A..H)
  line_variants.csv   variantes (couleurs/secteurs) des lignes urbaines
  route_steps.csv     arrêts séquentiels de chaque variante (alternatives "A / B" = même rang)
  suburban_links.csv  liaisons Primus -> Terminus (aucun arrêt intermédiaire inventé)
  places.csv          lieux uniques (clé normalisée) cités dans le corpus
"""
from __future__ import annotations

import re
from collections import OrderedDict

import pandas as pd

from planner.core.text import basic_norm, norm, parse_place_label, slug
from planner.settings import get_settings

COLOR_WORDS = {
    "manga": "bleu", "mena": "rouge", "maintso": "vert", "maitso": "vert", "mavo": "jaune", "fotsy": "blanc",
    "mainty": "noir",
}

RE_URBAN_SECTION = re.compile(r"^---\s*ZONE URBAINE", re.I)
RE_SUBURBAN_SECTION = re.compile(r"^---\s*ZONE SUBURBAINE", re.I)
RE_LINE = re.compile(r"^Ligne\s+(?P<code>[^()]+?)\s*(?:\((?P<note>[^)]*)\))?\s*$")
RE_SECTOR = re.compile(r"^-\s*Secteur\s+(?P<name>.+?)\s*:\s*$", re.I)
RE_TRAJET = re.compile(r"^[-*]\s*Trajet\s*(?:\((?P<variant>[^)]*)\))?\s*:\s*(?P<stops>.+)$", re.I)
RE_SUB_LINE = re.compile(r"^LIGNE\s+(?P<code>[A-Z]{1,2})\s*(?:\((?P<note>[^)]*)\))?\s*:?\s*$", re.I)
RE_LINK = re.compile(r"^[*•\-]\s*Primus\s*:\s*(?P<primus>.+?)\s*-+>\s*Terminus\s*:\s*(?P<terminus>.+?)\s*$")
STOP_SEP = re.compile(r"\s+-\s+")
NOTE_HINT = " — pour une précision libre, commencer la ligne par « Note : »"
# Lignes de commentaire / précision libres (conservées dans notes, sans effet sur le réseau).
RE_NOTE = re.compile(r"^(#|//|NB\b|N\.B\.|Note\b|Remarque\b|Précision\b|Precision\b|Clarification\b)", re.I)


def _colors(variant: str | None) -> str | None:
    if not variant:
        return None
    b = basic_norm(variant)
    if "tsipika" in b:  # « Misy / Tsy misy tsipika mena » = avec / sans liseré rouge
        return "sans liseré rouge" if b.startswith("tsy ") else "liseré rouge"
    found = [COLOR_WORDS[t] for t in re.split(r"[\s\-]+", basic_norm(variant)) if t in COLOR_WORDS]
    return "-".join(found) or None


class PlaceRegistry:
    def __init__(self) -> None:
        self.places: OrderedDict[str, dict] = OrderedDict()

    def add(self, alt: dict, zone: str, role: str) -> str:
        key = norm(alt["name"])
        pid = slug(alt["name"])
        p = self.places.setdefault(pid, {
            "place_id": pid, "norm_key": key, "display_name": alt["name"].strip(),
            "raw_labels": [], "qualifiers": [], "contexts": [], "vias": [], "zones": [], "roles": [], "occurrences": 0,
        })
        p["occurrences"] += 1
        for field, val in (("raw_labels", alt["raw"]), ("qualifiers", alt["qualifier"]),
                           ("contexts", alt["context"]), ("vias", alt["via"]), ("zones", zone), ("roles", role)):
            if val and val not in p[field]:
                p[field].append(val)
        # Préférer une graphie en casse mixte comme libellé d'affichage (ex. "Homi" vs "HOMI").
        if p["display_name"].isupper() and not alt["name"].isupper():
            p["display_name"] = alt["name"].strip()
        return pid

    def frame(self) -> pd.DataFrame:
        rows = []
        for p in self.places.values():
            rows.append({**p, **{k: " | ".join(p[k]) for k in ("raw_labels", "qualifiers", "contexts", "vias", "zones", "roles")}})
        return pd.DataFrame(rows)


def parse(path=None) -> dict[str, pd.DataFrame]:
    text = (path or get_settings().bus_txt).read_text(encoding="utf-8")
    reg = PlaceRegistry()
    lines, variants, steps, links, notes = [], [], [], [], []
    section = None
    cur_line = cur_sector = cur_sub = None

    for lineno, raw in enumerate(text.splitlines(), start=1):
        s = raw.strip()
        if not s or s.startswith("==="):
            continue
        if RE_NOTE.match(s):
            notes.append({"source_line": lineno, "section": section, "text": s})
            continue
        if RE_URBAN_SECTION.match(s):
            section = "urbaine"
            continue
        if RE_SUBURBAN_SECTION.match(s):
            section = "suburbaine"
            continue

        if section == "urbaine":
            if m := RE_LINE.match(s):
                code = re.sub(r"\s+", " ", m.group("code")).strip()
                cur_line = {"line_id": "U-" + code.replace(" ", ""), "line_code": code, "zone": "urbaine",
                            "group": None, "note": m.group("note"), "source_line": lineno}
                lines.append(cur_line)
                cur_sector = None
                continue
            if m := RE_SECTOR.match(s):
                cur_sector = m.group("name").strip()
                continue
            if m := RE_TRAJET.match(s):
                assert cur_line is not None, f"Trajet hors ligne (l.{lineno})"
                vlabel = (m.group("variant") or "").strip() or None
                labels = [x.strip() for x in STOP_SEP.split(m.group("stops").strip()) if x.strip()]
                n = sum(1 for v in variants if v["line_id"] == cur_line["line_id"]) + 1
                vid = f"{cur_line['line_id']}#{n}"
                first_key, last_key = norm(labels[0]), norm(labels[-1])
                variants.append({
                    "variant_id": vid, "line_id": cur_line["line_id"],
                    "variant_label": vlabel or "Unique", "sector": cur_sector, "color": _colors(vlabel),
                    "is_loop": first_key == last_key and len(labels) > 2,
                    "n_steps": len(labels), "raw_text": m.group("stops").strip(), "source_line": lineno,
                })
                for seq, lab in enumerate(labels, start=1):
                    for ai, alt in enumerate(parse_place_label(lab)):
                        pid = reg.add(alt, "urbaine", "arret")
                        steps.append({"variant_id": vid, "seq": seq, "alt_index": ai, "place_id": pid,
                                      "raw_label": lab, "qualifier": alt["qualifier"], "annotation": alt["annotation"]})
                continue
            raise ValueError(f"Ligne non reconnue (zone urbaine, l.{lineno}) : {s!r}{NOTE_HINT}")

        if section == "suburbaine":
            if m := RE_SUB_LINE.match(s):
                code = m.group("code").upper()
                cur_sub = {"line_id": f"S-{code}", "line_code": f"Ligne {code}", "zone": "suburbaine",
                           "group": code, "note": m.group("note"), "source_line": lineno}
                lines.append(cur_sub)
                continue
            if m := RE_LINK.match(s):
                assert cur_sub is not None
                p_raw = m.group("primus").rstrip("- ").strip()
                t_raw = m.group("terminus").strip()
                p_alt = parse_place_label(p_raw)[0]
                t_alt = parse_place_label(t_raw)[0]
                n = sum(1 for k in links if k["line_id"] == cur_sub["line_id"]) + 1
                links.append({
                    "link_id": f"{cur_sub['line_id']}#{n}", "line_id": cur_sub["line_id"],
                    "primus_raw": p_raw, "primus_place_id": reg.add(p_alt, "suburbaine", "primus"),
                    "primus_context": p_alt["context"], "primus_qualifier": p_alt["qualifier"],
                    "terminus_raw": t_raw, "terminus_place_id": reg.add(t_alt, "suburbaine", "terminus"),
                    "terminus_qualifier": t_alt["qualifier"], "via_mention": t_alt["via"] or p_alt["via"],
                    "intermediate_stops": "inconnus (non fournis par la source)", "source_line": lineno,
                })
                continue
            raise ValueError(f"Ligne non reconnue (zone suburbaine, l.{lineno}) : {s!r}{NOTE_HINT}")

    df_lines = pd.DataFrame(lines)
    df_var = pd.DataFrame(variants)
    df_links = pd.DataFrame(links)
    nvar = df_var.groupby("line_id").size()
    nlink = df_links.groupby("line_id").size()
    df_lines["n_variants"] = df_lines.line_id.map(nvar).fillna(df_lines.line_id.map(nlink)).fillna(0).astype(int)
    return {
        "lines": df_lines, "line_variants": df_var, "route_steps": pd.DataFrame(steps),
        "suburban_links": df_links, "places": reg.frame(),
        "corpus_notes": pd.DataFrame(notes, columns=["source_line", "section", "text"]),
    }


def build() -> dict[str, int]:
    get_settings().tables_dir.mkdir(parents=True, exist_ok=True)
    tables = parse()
    for name, df in tables.items():
        df.to_csv(get_settings().tables_dir / f"{name}.csv", index=False)
    lines = tables["lines"]
    return {
        "lignes_urbaines": int((lines.zone == "urbaine").sum()),
        "variantes_urbaines": len(tables["line_variants"]),
        "groupes_suburbains": int((lines.zone == "suburbaine").sum()),
        "liaisons_suburbaines": len(tables["suburban_links"]),
        "etapes_urbaines": len(tables["route_steps"]),
        "lieux_uniques": len(tables["places"]),
        "notes_corpus": len(tables["corpus_notes"]),
    }


if __name__ == "__main__":
    for k, v in build().items():
        print(f"{k:24s} {v}")
