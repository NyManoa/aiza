/* Hooks de données (TanStack Query) : cache, déduplication, annulation automatique. */
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { apiGet } from "./client";
import type {
  AdminUnit, EndpointInfo, FokontanyItem, LinesResponse, Meta, Place, Region, RouteResponse, SearchResult, Stats,
} from "./types";

const STATIC = { staleTime: Infinity, gcTime: Infinity } as const; // référentiel immuable entre deux builds

export const qk = {
  meta: ["meta"] as const,
  regions: ["regions"] as const,
  districts: (r: string) => ["districts", r] as const,
  communes: (d: string) => ["communes", d] as const,
  fokontanyList: (c: string) => ["fokontany-list", c] as const,
  fokontany: (f: string) => ["fokontany", f] as const,
  search: (q: string) => ["search", q] as const,
  itineraries: (a: string, b: string, k: number) => ["itineraries", a, b, k] as const,
  lines: ["lines"] as const,
  places: ["places"] as const,
  stats: ["stats"] as const,
};

export const useMeta = () => useQuery({ queryKey: qk.meta, queryFn: ({ signal }) => apiGet<Meta>("/meta", undefined, signal), ...STATIC });

export const useRegions = () =>
  useQuery({ queryKey: qk.regions, queryFn: ({ signal }) => apiGet<Region[]>("/regions", undefined, signal), ...STATIC });

export const useDistricts = (region: string | null) =>
  useQuery({
    queryKey: qk.districts(region ?? ""), enabled: !!region, ...STATIC,
    queryFn: ({ signal }) => apiGet<AdminUnit[]>(`/regions/${region}/districts`, undefined, signal),
  });

export const useCommunes = (district: string | null) =>
  useQuery({
    queryKey: qk.communes(district ?? ""), enabled: !!district, ...STATIC,
    queryFn: ({ signal }) => apiGet<AdminUnit[]>(`/districts/${district}/communes`, undefined, signal),
  });

export const useFokontanyList = (commune: string | null) =>
  useQuery({
    queryKey: qk.fokontanyList(commune ?? ""), enabled: !!commune, ...STATIC,
    queryFn: ({ signal }) => apiGet<FokontanyItem[]>(`/communes/${commune}/fokontany`, undefined, signal),
  });

export const useFokontany = (code: string | null) =>
  useQuery({
    queryKey: qk.fokontany(code ?? ""), enabled: !!code, ...STATIC,
    queryFn: ({ signal }) => apiGet<EndpointInfo>(`/fokontany/${code}`, undefined, signal),
  });

export const useSearch = (q: string) =>
  useQuery({
    queryKey: qk.search(q), enabled: q.length >= 2, staleTime: 5 * 60_000, placeholderData: keepPreviousData,
    queryFn: ({ signal }) => apiGet<SearchResult[]>("/search", { q, limit: 15 }, signal),
  });

export const useItineraries = (from: string | null, to: string | null, maxTransfers: number) =>
  useQuery({
    queryKey: qk.itineraries(from ?? "", to ?? "", maxTransfers), enabled: !!from && !!to, ...STATIC,
    queryFn: ({ signal }) => apiGet<RouteResponse>("/itineraries", { from, to, max_transfers: maxTransfers }, signal),
  });

export const useLines = () =>
  useQuery({ queryKey: qk.lines, queryFn: ({ signal }) => apiGet<LinesResponse>("/network/lines", undefined, signal), ...STATIC });

export const usePlaces = () =>
  useQuery({ queryKey: qk.places, queryFn: ({ signal }) => apiGet<Place[]>("/network/places", undefined, signal), ...STATIC });

export const useStats = () =>
  useQuery({ queryKey: qk.stats, queryFn: ({ signal }) => apiGet<Stats>("/stats", undefined, signal), ...STATIC });
