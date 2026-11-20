import type { Itinerary } from "../../api/types";

export type ZoneKind = "urbaine" | "suburbaine" | "mixte";
export type SortKey = "recommande" | "plus_court" | "moins_de_marche" | "moins_de_correspondances";

export interface ItineraryFilters {
  transfers: number[];          // 0, 1, 2 et 3 (= 3 correspondances ou plus, palier « approche »)
  zones: ZoneKind[];
  minConfidence: number;
  publishedDirectionOnly: boolean;
  noWalk: boolean;
  publishedStopsOnly: boolean;   // exclut les accès « en passage » (fokontany traversé estimé)
  sort: SortKey;
}

export const DEFAULT_FILTERS: ItineraryFilters = {
  transfers: [0, 1, 2, 3], zones: ["urbaine", "suburbaine", "mixte"], minConfidence: 0,
  publishedDirectionOnly: false, noWalk: false, publishedStopsOnly: false, sort: "recommande",
};

export const zoneKind = (it: Pick<Itinerary, "zones">): ZoneKind =>
  it.zones.length > 1 ? "mixte" : (it.zones[0] ?? "urbaine");

const SORTS: Record<SortKey, (a: Itinerary, b: Itinerary) => number> = {
  recommande: (a, b) => b.score - a.score || a.id - b.id,
  plus_court: (a, b) => a.total_km - b.total_km || b.score - a.score || a.id - b.id,
  moins_de_marche: (a, b) => a.walk_km - b.walk_km || b.score - a.score || a.id - b.id,
  moins_de_correspondances: (a, b) => a.transfers - b.transfers || b.score - a.score || a.id - b.id,
};

export function applyFilters(items: Itinerary[], f: ItineraryFilters): Itinerary[] {
  return items
    .filter((it) =>
      f.transfers.includes(Math.min(it.transfers, 3))
      && f.zones.includes(zoneKind(it))
      && it.confidence_min >= f.minConfidence
      && !(f.publishedDirectionOnly && it.has_reverse)
      && !(f.noWalk && it.has_walk)
      && !(f.publishedStopsOnly && it.has_passage))
    .sort(SORTS[f.sort]);
}

export function toggle<T>(list: T[], value: T): T[] {
  return list.includes(value) ? list.filter((v) => v !== value) : [...list, value];
}
