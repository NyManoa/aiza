/* Types alignés sur les schémas Pydantic du backend (backend/src/planner/api/schemas). */

export type MatchStatus =
  | "exact_fokontany" | "sous_chaine_fokontany" | "commune" | "repere_ou_variante" | "non_resolu" | "non_desservi"
  | "passage_declare" | "passage_estime";
export type Coverage = "direct" | "commune" | "passage" | "aucune";
export type AccessMode = "direct" | "commune" | "passage" | "proche_a_pied" | "repli_a_pied" | "approche_a_pied";
export type SearchMode = "normal" | "acces_elargi" | "approche";
export type Zone = "urbaine" | "suburbaine";

export interface ServedSummary {
  n_places: number; n_direct: number; n_passage: number; n_lines: number;
  best_status: MatchStatus; best_confidence: number; coverage: Coverage;
}
export interface AdminUnit { pcode: string; name: string; area_sqkm: number | null; n_children: number }
export interface Region extends AdminUnit { old_province: string | null }
export interface FokontanyItem { pcode: string; name: string; area_sqkm: number | null; served: ServedSummary }

export interface FokontanyLabel {
  adm4_pcode: string; adm4_name: string; adm3_pcode: string; adm3_name: string;
  adm2_pcode: string; adm2_name: string; adm1_pcode: string; adm1_name: string;
  area_sqkm: number | null; lat: number | null; lon: number | null;
}
export interface SearchResult extends FokontanyLabel {
  match: "pcode" | "nom" | "arret"; via_place: string | null; served: ServedSummary;
}

export interface PlaceSummary {
  place_id: string; name: string; match_status: MatchStatus; confidence: number;
  fokontany: string[]; communes: string[]; match_detail: string; n_lines: number;
  virtual: boolean; lat: number | null; lon: number | null; coord_quality: string;
}
export interface Access {
  place: PlaceSummary; mode: AccessMode; status: MatchStatus;
  confidence: number; walk_km: number;
  via_fokontany: { adm4_pcode: string; adm4_name: string; relation: string } | null;
}
export interface Fallback {
  adm4_pcode: string; adm4_name: string; adm3_name: string; ring: number | null;
  distance_km: number; within_limit: boolean; relation: string;
}
export interface LineHere {
  service_id: string; line_code: string; zone: Zone; variant: string; place: string;
  from: string; to: string; passage: boolean; other_end_unresolved: boolean;
}
export interface EndpointInfo {
  fokontany: FokontanyLabel; served: ServedSummary; access: Access[];
  fallback: Fallback[]; warnings: string[]; lines_here: LineHere[];
}

export interface Leg {
  service_id: string; line_id: string; line_code: string; zone: Zone; variant: string;
  sector: string | null; color: string | null; note: string | null; loop: boolean;
  from: PlaceSummary; to: PlaceSummary; direction: "aller" | "retour_suppose"; wrap: boolean;
  n_segments: number | null; stops: string[]; passages: string[]; km: number; km_unknown: number; headsign: string;
  stops_known: boolean; via_mention: string | null; raw: string;
}
export interface TransferPoint {
  at: PlaceSummary; to: PlaceSummary; type: "meme_lieu" | "a_pied_meme_fokontany"; fokontany: string | null;
  walk_km: number;
}
export interface Itinerary {
  id: number; transfers: number; score: number; score_breakdown: Record<string, number>;
  legs: Leg[]; transfer_points: TransferPoint[]; line_ids: string[]; zones: Zone[];
  confidence_min: number; statuses: MatchStatus[];
  access: { origin: Access; destination: Access };
  bus_km: number; walk_km: number; total_km: number; direct_km: number | null; detour_ratio: number | null;
  is_detour: boolean; revisits: number;
  has_reverse: boolean; has_walk: boolean; has_passage: boolean; signature: string;
}
export interface RouteResponse {
  origin: EndpointInfo; destination: EndpointInfo; itineraries: Itinerary[];
  counts: Record<string, number>; messages: string[]; max_transfers: number; direct_km: number | null;
  pruned: Partial<Record<"doublons" | "domines" | "va_et_vient" | "detours", number>>;
  highlights: Partial<Record<Highlight, number | null>>;
  search_mode: SearchMode;
}

export type Highlight = "recommande" | "plus_court" | "moins_de_marche" | "moins_de_correspondances";

export interface Meta {
  version: string; n_regions: number; n_fokontany: number; n_fokontany_served: number;
  default_region: string; max_transfers: number; max_walk_km: number; max_rings: number;
  weights: Record<string, number>; network: { components: number[]; n_places: number; n_services: number };
}

export interface Line { line_id: string; line_code: string; zone: Zone; group: string | null; note: string | null; n_variants: number }
export interface Service {
  id: string; line_id: string; line_code: string; zone: Zone; label: string; sector: string | null;
  color: string | null; note: string | null; loop: boolean; stops: string[][]; stops_named: string[][];
  stops_known: boolean; via_mention: string | null; raw: string;
  seg_km: (number | null)[]; corridor_named: { adm4_pcode: string; name: string; source: string }[][]; length_km: number;
}
export interface LinesResponse { lines: Line[]; services: Service[] }
export interface Place {
  place_id: string; name: string; match_status: MatchStatus; confidence: number; n_lines: number;
  n_passages: number; match_detail: string; roles: string;
}

/* ---- Statistiques (analysis/stats.json) ---- */
export interface CoverageRow {
  adm2_name: string; adm3_name?: string; adm2_pcode?: string; adm3_pcode?: string; tier: number;
  n_fokontany: number; direct: number; faible: number; passage: number; commune: number; aucune: number;
  area_sqkm: number; area_direct_sqkm: number; mean_lines_direct: number;
  pct_fokontany_direct: number; pct_area_direct: number;
}
export interface Stats {
  matching: {
    n_places: number; resolved_places: number; resolved_places_pct: number; n_occurrences: number;
    resolved_occurrences: number; resolved_occurrences_pct: number;
    by_status_places: Record<string, number>; by_status_occurrences: Record<string, number>;
    confidence_distribution: Record<string, number>;
    unresolved: { place_id: string; name: string; occurrences: number; n_lines: number; roles: string }[];
  };
  network: {
    urban_lines: number; urban_variants: number; loop_variants: number; suburban_groups: number;
    suburban_links: number; nodes: number; edges_declared: number; edges_reverse_assumed: number;
    components: number[]; transfer_nodes: number; coord_quality: Record<string, number>;
    corridor_segments: { estimes: number; declares: number; fokontany_distincts: number }; network_length_km: number;
    top_nodes_by_lines: { place_id: string; name: string; n_lines: number; n_passages: number;
      in_degree: number; out_degree: number; match_status: MatchStatus; confidence: number }[];
  };
  coverage: {
    n_fokontany: number; n_core: number;
    by_coverage: Record<string, number>; by_coverage_core: Record<string, number>;
    lines_per_fokontany_distribution_core: Record<string, number>;
    rings_distribution_core: Record<string, number>;
    by_district: CoverageRow[]; by_commune_core: CoverageRow[];
    top_fokontany_by_lines: { adm4_pcode: string; adm4_name: string; adm3_name: string;
      n_lines_direct: number; best_status: MatchStatus; best_confidence: number }[];
    unserved_core_largest: { adm4_pcode: string; adm4_name: string; adm3_name: string;
      area_sqkm: number; rings_to_network: number | null }[];
    unserved_urban: { adm4_pcode: string; adm4_name: string; adm3_name: string;
      coverage: Coverage; rings_to_network: number | null }[];
    low_service_core: { adm4_pcode: string; adm4_name: string; adm3_name: string; best_status: MatchStatus }[];
  };
}
