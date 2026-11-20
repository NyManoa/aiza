"""Règles déterministes de normalisation de chaînes et d'analyse des libellés de lieux."""
from __future__ import annotations

import csv
import re
import unicodedata
from functools import lru_cache

from planner.settings import get_settings

_APOS = re.compile(r"[’'`´]")
_NON_ALNUM = re.compile(r"[^a-z0-9 ]+")
_SPACES = re.compile(r"\s+")
_HA = re.compile(r"\b(\d+)\s*ha\b")

# Suffixes/qualificatifs ignorables lors d'une seconde tentative (pénalisée).
IGNORABLE_SUFFIXES = {
    "nord", "sud", "est", "ouest", "avaratra", "atsimo", "atsinanana", "andrefana",
    "ambony", "ambany", "afovoany", "hopitaly", "commune", "cite", "tanana", "rova",
    "plaque", "centre", "gara",
    # Jours de marché (préfixes usuels : « Alakamisy Antanimarina ») — les noms officiels qui les contiennent
    # (Talata Volonondry, Sabotsy Namehana…) sont rattachés exactement au premier passage, avant ce retrait.
    "alatsinainy", "talata", "alarobia", "alakamisy", "zoma", "sabotsy", "alahady",
}
# Annotations entre parenthèses qui ne sont pas des lieux.
NON_PLACE_ANNOTATIONS = {"cycle", "mazda"}


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


@lru_cache(maxsize=1)
def token_aliases() -> dict[str, str]:
    aliases: dict[str, str] = {}
    if get_settings().token_aliases_csv.exists():
        with open(get_settings().token_aliases_csv, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                aliases[basic_norm(row["token"])] = basic_norm(row["canonical"])
    return aliases


def basic_norm(text: str) -> str:
    """Casse, accents, apostrophes, traits d'union, ponctuation, espaces."""
    s = strip_accents(str(text)).lower()
    s = _APOS.sub(" ", s)
    s = s.replace("-", " ").replace("/", " ")
    s = _NON_ALNUM.sub(" ", s)
    s = _HA.sub(r"\1ha", s)
    return _SPACES.sub(" ", s).strip()


def norm(text: str) -> str:
    """Normalisation complète = basic_norm + table d'alias de tokens (éditable)."""
    aliases = token_aliases()
    return " ".join(aliases.get(t, t) for t in basic_norm(text).split())


def tokens(text: str) -> list[str]:
    return norm(text).split()


def contains_tokens(haystack: list[str], needle: list[str]) -> bool:
    """Vrai si `needle` apparaît comme suite contiguë de mots entiers dans `haystack`."""
    n = len(needle)
    if n == 0 or n > len(haystack):
        return False
    return any(haystack[i:i + n] == needle for i in range(len(haystack) - n + 1))


def strip_suffixes(toks: list[str]) -> list[str]:
    """Retire les qualificatifs ignorables (en fin ou en tête) ; garde au moins un token."""
    out = [t for t in toks if t not in IGNORABLE_SUFFIXES]
    return out if out else toks


def slug(text: str) -> str:
    return norm(text).replace(" ", "_") or "vide"


_PAREN = re.compile(r"\(([^)]*)\)")
# « Passant par X » / « Via X » : mention informative du trajet, jamais un arrêt.
_VIA = re.compile(r"\b(?:passant\s+par|via)\b", re.IGNORECASE)


def parse_place_label(raw: str) -> list[dict]:
    """Découpe un libellé brut en une ou plusieurs alternatives structurées.

    Exemples :
      "Antananarivo (67 HA)"           -> name="67 HA", context="Antananarivo"
      "Ivato (Passant par Ambohijanahary)" -> name="Ivato", via="Ambohijanahary"
      "Ambatomaro/Antsobolo"           -> 2 alternatives
      "Antanetibe (Ambatobe)"          -> name="Antanetibe", qualifier="Ambatobe"
    """
    raw = raw.strip()
    via = None
    qualifiers: list[str] = []
    annotations: list[str] = []

    def _grab(m: re.Match) -> str:
        inner = m.group(1).strip()
        nonlocal via
        if _VIA.search(inner):
            via = _VIA.split(inner, maxsplit=1)[1].strip()
        elif basic_norm(inner) in NON_PLACE_ANNOTATIONS:
            annotations.append(inner)
        elif inner:
            qualifiers.append(inner)
        return " "
    core = _PAREN.sub(_grab, raw)
    if _VIA.search(core):
        core, via_txt = _VIA.split(core, maxsplit=1)
        via = via_txt.strip()
    core = _SPACES.sub(" ", core).strip()

    context = None
    # "Antananarivo (Gare X)" : la gare/le repère est le vrai lieu d'embarquement.
    if basic_norm(core) == "antananarivo" and qualifiers:
        context, core = "Antananarivo", qualifiers.pop(0)

    alternatives = [a.strip() for a in core.split("/") if a.strip()] or [core]
    return [
        {
            "raw": raw,
            "name": alt,
            "qualifier": " / ".join(qualifiers) or None,
            "context": context,
            "via": via,
            "annotation": " / ".join(annotations) or None,
            "is_alternative": len(alternatives) > 1,
        }
        for alt in alternatives
    ]
