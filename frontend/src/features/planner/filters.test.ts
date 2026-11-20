import { describe, expect, it } from "vitest";

import type { Itinerary } from "../../api/types";
import { applyFilters, DEFAULT_FILTERS, toggle, zoneKind } from "./filters";

const it0 = (p: Partial<Itinerary>): Itinerary => ({
  id: 1, transfers: 0, score: 90, score_breakdown: {}, legs: [], transfer_points: [], line_ids: [],
  zones: ["urbaine"], confidence_min: 1, statuses: [], access: {} as Itinerary["access"],
  bus_km: 5, walk_km: 0, total_km: 5, direct_km: 4, detour_ratio: 1.25, is_detour: false, revisits: 0,
  has_reverse: false, has_walk: false, has_passage: false, signature: "", ...p,
});

describe("filtres d'itinéraires", () => {
  const items = [
    it0({ id: 1 }),
    it0({ id: 2, transfers: 1, score: 70, total_km: 3, zones: ["suburbaine", "urbaine"], has_reverse: true }),
    it0({ id: 3, transfers: 2, score: 50, total_km: 4, walk_km: 1, zones: ["suburbaine"], confidence_min: 0.5,
      has_walk: true, has_passage: true }),
  ];

  it("classe le type de ligne", () => {
    expect(items.map(zoneKind)).toEqual(["urbaine", "mixte", "suburbaine"]);
  });

  it("laisse tout passer par défaut", () => {
    expect(applyFilters(items, DEFAULT_FILTERS)).toHaveLength(3);
  });

  it("combine les critères", () => {
    const r = applyFilters(items, { ...DEFAULT_FILTERS, minConfidence: 0.65, publishedDirectionOnly: true });
    expect(r.map((i) => i.id)).toEqual([1]);
    expect(applyFilters(items, { ...DEFAULT_FILTERS, transfers: [2], noWalk: true })).toHaveLength(0);
    expect(applyFilters(items, { ...DEFAULT_FILTERS, zones: ["mixte"] }).map((i) => i.id)).toEqual([2]);
  });

  it("trie selon le critère choisi", () => {
    expect(applyFilters(items, DEFAULT_FILTERS).map((i) => i.id)).toEqual([1, 2, 3]);
    expect(applyFilters(items, { ...DEFAULT_FILTERS, sort: "plus_court" }).map((i) => i.id)).toEqual([2, 3, 1]);
    expect(applyFilters(items, { ...DEFAULT_FILTERS, sort: "moins_de_marche" }).map((i) => i.id)).toEqual([1, 2, 3]);
  });

  it("peut exclure les accès en passage", () => {
    expect(applyFilters(items, { ...DEFAULT_FILTERS, publishedStopsOnly: true }).map((i) => i.id)).toEqual([1, 2]);
  });

  it("garde les itinéraires à 3+ correspondances par défaut", () => {
    const many = [it0({ id: 9, transfers: 4 })];
    expect(applyFilters(many, DEFAULT_FILTERS)).toHaveLength(1);
    expect(applyFilters(many, { ...DEFAULT_FILTERS, transfers: [0, 1, 2] })).toHaveLength(0);
  });

  it("bascule une valeur", () => {
    expect(toggle([0, 1], 1)).toEqual([0]);
    expect(toggle([0], 2)).toEqual([0, 2]);
  });
});
