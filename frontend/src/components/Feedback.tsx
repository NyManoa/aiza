import type { ReactNode } from "react";

import { ApiError } from "../api/client";

export const Alert = ({ tone = "info", children }: { tone?: "info" | "warn" | "bad"; children: ReactNode }) =>
  <div className={`alert ${tone}`} role={tone === "bad" ? "alert" : undefined}>{children}</div>;

export function ErrorBox({ error }: { error: unknown }) {
  const msg = error instanceof ApiError ? error.message
    : error instanceof Error ? error.message : "Erreur inconnue";
  return <Alert tone="bad">Erreur : {msg}. L'API est-elle disponible ?</Alert>;
}

export const Loading = ({ label = "Chargement…" }: { label?: string }) =>
  <p className="muted loading" aria-live="polite">{label}</p>;
