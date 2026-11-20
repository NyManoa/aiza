"""Règles métier explicites et versionnées (aucun paramètre appris).

Modifier une valeur ici change de façon traçable le rattachement, le repli ou le classement.
"""
from __future__ import annotations

# --- Périmètre ----------------------------------------------------------------
ANALAMANGA = "MG11"
# Niveau 1 : Antananarivo Renivohitra (6 arrondissements) = cœur du réseau urbain.
TIER1_DISTRICTS = frozenset({"MG11118", "MG11119", "MG11120", "MG11121", "MG11122", "MG11123"})
# Niveau 2 : périphérie immédiate (Atsimondrano, Avaradrano, Ambohidratrimo).
TIER2_DISTRICTS = frozenset({"MG11117", "MG11102", "MG11103"})
# Niveau 4 : régions limitrophes (Vakinankaratra, Itasy) — correspondances exactes uniquement.
NEIGHBOUR_REGIONS = {"MG12": 4, "MG13": 4}
CITY_CENTER = (-18.9100, 47.5250)  # Analakely (lat, lon) — départage des homonymes uniquement

# --- Confiance par règle de rattachement ---------------------------------------
CONFIDENCE = {
    "exact_fokontany": 1.00,
    "exact_fokontany_contexte": 0.95,
    "exact_fokontany_homonyme": 0.85,
    "sous_chaine_fokontany": 0.75,
    "sous_chaine_fokontany_large": 0.65,
    "commune": 0.50,
    "commune_sous_chaine": 0.40,
    "repere_ou_variante": 0.60,
    "qualificatif_seul": 0.45,
    "non_resolu": 0.0,
}
PUBLIC_STATUSES = ("exact_fokontany", "sous_chaine_fokontany", "commune", "repere_ou_variante", "non_resolu")
PASSAGE_STATUSES = ("passage_declare", "passage_estime")
SUFFIX_PENALTY = 0.10
MAX_SUBSTRING_CANDIDATES = 8
DIR_MARGIN_DEG = 0.01
ANCHOR_MAX_KM = 5.0
ANCHOR_FAR_PENALTY = 0.20
# Cohérence d'itinéraire : un rattachement automatique situé à plus de ROUTE_CONSISTENCY_KM de la position
# moyenne de ses arrêts voisins (sur les lignes urbaines) est remplacé par un candidat nettement plus proche.
ROUTE_CONSISTENCY_KM = 3.0
ROUTE_CONSISTENCY_PENALTY = 0.05

# --- Géométrie et fokontany traversés ------------------------------------------
# Distances « à vol d'oiseau » entre centroïdes (référentiel OCHA) : ordre de grandeur, pas un kilométrage routier.
CORRIDOR_MAX_RATIO = 1.8        # chemin de voisinage accepté si <= ratio x distance directe + marge
CORRIDOR_MARGIN_KM = 0.8
CORRIDOR_CONFIDENCE = 0.35      # fokontany traversé estimé (plus court chemin de voisinage entre deux arrêts)
DECLARED_CORRIDOR_CONFIDENCE = 0.70  # fokontany traversé déclaré dans data/reference/line_fokontany.csv
COORD_ESTIMATION_ROUNDS = 5     # interpolation des repères non rattachés à partir des arrêts voisins
DEFAULT_SEGMENT_KM = 1.2        # tronçon de longueur inconnue (repère sans coordonnée)

# --- Repli (faible desserte) ---------------------------------------------------
FALLBACK_MAX_RINGS = 3
FALLBACK_MAX_KM = 6.0
FALLBACK_ALTERNATIVES = 3
LOW_SERVICE_MAX_LINES = 1

# --- Accès ------------------------------------------------------------------------
NEARBY_ACCESS_KM = 1.5          # arrêts des fokontany voisins rejoignables à pied (toujours proposés)
NEARBY_ACCESS_RINGS = 2
WALK_TRANSFER_DEFAULT_KM = 0.4  # correspondance à pied dans un même fokontany, positions inconnues
DEFAULT_SUBURBAN_KM = 10.0      # liaison suburbaine dont une extrémité n'a pas de coordonnée

# --- Recherche par paliers (un itinéraire est TOUJOURS proposé) ----------------------
# 1. normal ; 2. accès élargi : + les EXTENDED_ACCESS_K arrêts les plus proches de chaque extrémité (toute distance) ;
# 3. approche : bus jusqu'au point du réseau le plus proche de l'arrivée, puis marche (APPROACH_MAX_TRANSFERS max).
EXTENDED_ACCESS_K = 12
APPROACH_MAX_LEGS = 5           # palier « approche » : plus court chemin pondéré (Dijkstra), jusqu'à 4 correspondances
APPROACH_RESULTS = 5

# --- Élimination des trajets inutiles (va-et-vient, détours) ------------------------
# Un itinéraire est retiré s'il existe une alternative « propre » avec au plus autant de correspondances :
#  - va-et-vient : il repasse par un même lieu ;
#  - détour : distance totale > MAX_DETOUR_RATIO x distance directe ET > distance directe + MAX_DETOUR_EXTRA_KM.
MAX_DETOUR_RATIO = 2.2
MAX_DETOUR_EXTRA_KM = 3.0

# --- Score de classement (transparent) ------------------------------------------
SCORE_BASE = 100.0
W_TRANSFER = 20.0       # par correspondance
W_WALK_TRANSFER = 3.0   # par correspondance à pied
W_WALK_ACCESS = 5.0     # par extrémité rejointe à pied hors du fokontany (repli / arrêt proche)
W_WALK_KM = 4.0         # par km de marche (accès + correspondances), jusqu'à FALLBACK_MAX_KM
W_WALK_FAR_KM = 10.0    # par km de marche AU-DELÀ de FALLBACK_MAX_KM (marche très longue fortement pénalisée)
W_BUS_KM = 1.2          # par km en bus (vol d'oiseau entre arrêts)
W_UNKNOWN_KM = 3.0      # par tronçon de longueur inconnue
W_CONFIDENCE = 25.0     # x (1 - confiance minimale départ/arrivée)
W_REVERSE = 4.0         # par tronçon en sens retour supposé
W_WRAP = 3.0            # par passage au terminus d'une boucle
W_REVISIT = 12.0        # par lieu traversé deux fois (va-et-vient)
W_STOP = 0.2            # par arrêt intermédiaire publié
MAX_RESULTS_PER_CATEGORY = 40
MAX_TRANSFERS = 2


def score_weights() -> dict[str, float]:
    return {"base": SCORE_BASE, "transfer": W_TRANSFER, "walk_transfer": W_WALK_TRANSFER,
            "walk_access": W_WALK_ACCESS, "walk_km": W_WALK_KM, "walk_far_km": W_WALK_FAR_KM,
            "bus_km": W_BUS_KM, "unknown_km": W_UNKNOWN_KM,
            "confidence": W_CONFIDENCE, "reverse": W_REVERSE, "wrap": W_WRAP, "revisit": W_REVISIT, "stop": W_STOP,
            "max_detour_ratio": MAX_DETOUR_RATIO, "max_detour_extra_km": MAX_DETOUR_EXTRA_KM,
            "nearby_access_km": NEARBY_ACCESS_KM}
