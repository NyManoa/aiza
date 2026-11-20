/* Client HTTP minimal : base configurable (VITE_API_BASE_URL), erreurs typées, annulation. */

export const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") || "/api/v1";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

type Query = Record<string, string | number | undefined | null>;

export function buildUrl(path: string, query?: Query): string {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(query ?? {})) if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
  const s = qs.toString();
  return `${API_BASE}${path}${s ? `?${s}` : ""}`;
}

export async function apiGet<T>(path: string, query?: Query, signal?: AbortSignal): Promise<T> {
  const res = await fetch(buildUrl(path, query), { signal, headers: { Accept: "application/json" } });
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    throw new ApiError(res.status, `Réponse invalide du serveur (HTTP ${res.status}).`);
  }
  if (!res.ok) {
    const detail = (body as { detail?: unknown })?.detail;
    const msg = typeof detail === "string" ? detail : Array.isArray(detail) ? "Paramètres invalides." : `HTTP ${res.status}`;
    throw new ApiError(res.status, msg);
  }
  return body as T;
}
