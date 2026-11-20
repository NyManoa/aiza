import type { AccessMode, Coverage, Highlight, MatchStatus } from "../api/types";

export const STATUS_LABEL: Record<MatchStatus, string> = {
  exact_fokontany: "exact fokontany",
  sous_chaine_fokontany: "sous-chaîne fokontany",
  commune: "commune",
  repere_ou_variante: "repère / variante",
  non_resolu: "non résolu",
  non_desservi: "non desservi",
  passage_declare: "passage déclaré",
  passage_estime: "passage estimé",
};

export const ACCESS_LABEL: Record<AccessMode, string> = {
  direct: "arrêt dans le fokontany",
  commune: "rattachement communal (approximatif)",
  passage: "ligne traversant le fokontany (passage)",
  proche_a_pied: "arrêt proche à pied",
  repli_a_pied: "arrêt le plus proche à pied",
  approche_a_pied: "approche : fin du trajet à pied",
};

export const COVERAGE_LABEL: Record<Coverage, string> = {
  direct: "desservi",
  commune: "desserte communale",
  passage: "traversé (estimé)",
  aucune: "sans ligne directe",
};

export const COVERAGE_GLYPH: Record<Coverage, string> = { direct: "●", commune: "◐", passage: "◌", aucune: "○" };

export const SCORE_LABEL: Record<string, string> = {
  base: "Base",
  correspondances: "Correspondances",
  correspondances_a_pied: "Correspondances à pied",
  acces_a_pied: "Extrémité rejointe à pied (arrêt proche / repli)",
  distance_a_pied: "Distance à pied",
  marche_au_dela_du_seuil: "Marche au-delà de 6 km",
  distance_en_bus: "Distance en bus",
  distance_inconnue: "Tronçons de longueur inconnue",
  va_et_vient: "Va-et-vient (lieu traversé deux fois)",
  confiance_rattachement: "Confiance du rattachement (min. départ/arrivée)",
  sens_retour_suppose: "Sens retour supposé",
  passage_terminus_boucle: "Passage au terminus d'une boucle",
  arrets_intermediaires: "Arrêts intermédiaires",
};

export const HIGHLIGHT_LABEL: Record<Highlight, string> = {
  recommande: "Recommandé",
  plus_court: "Plus court",
  moins_de_marche: "Moins de marche",
  moins_de_correspondances: "Moins de correspondances",
};

export const LINE_COLORS = ["bleu", "rouge", "vert", "jaune", "blanc", "noir"] as const;

export const kindLabel = (k: number) => (k === 0 ? "Direct" : `${k} correspondance${k > 1 ? "s" : ""}`);
