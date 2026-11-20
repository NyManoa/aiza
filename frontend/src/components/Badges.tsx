import type { ReactNode } from "react";

import type { Coverage, MatchStatus, ServedSummary, Zone } from "../api/types";
import { fmt } from "../lib/format";
import { COVERAGE_LABEL, LINE_COLORS, STATUS_LABEL } from "../lib/labels";

export function ConfidenceBadge({ status, confidence, label, showValue = true }:
  { status: MatchStatus; confidence?: number; label?: string; showValue?: boolean }) {
  const c = confidence ?? 0;
  const tone = confidence === undefined ? "b-neutral" : c >= 0.85 ? "b-ok" : c >= 0.6 ? "b-neutral" : c > 0 ? "b-warn" : "b-bad";
  return (
    <span className={`badge ${tone}`} title="Statut de rattachement et niveau de confiance">
      {label ?? STATUS_LABEL[status] ?? status}
      {showValue && confidence !== undefined && ` · ${fmt(confidence)}`}
    </span>
  );
}

export function CoverageBadge({ served }: { served: ServedSummary }) {
  const tone: Record<Coverage, string> = { direct: "b-ok", commune: "b-warn", passage: "b-warn", aucune: "b-bad" };
  return (
    <span className={`badge cov ${tone[served.coverage]}`}>
      {COVERAGE_LABEL[served.coverage]}
      {served.n_lines > 0 && ` · ${served.n_lines} ligne${served.n_lines > 1 ? "s" : ""}`}
    </span>
  );
}

export function ColorDots({ color }: { color: string | null }) {
  const dots = (color ?? "").split("-").filter((c): c is (typeof LINE_COLORS)[number] =>
    (LINE_COLORS as readonly string[]).includes(c));
  return <>{dots.map((c, i) => <span key={i} className={`dot ${c}`} title={c} />)}</>;
}

export function LineBadge({ zone, lineCode, variant, color }:
  { zone: Zone; lineCode: string; variant?: string | null; color?: string | null }) {
  const sub = zone === "suburbaine";
  return (
    <span className={`line-badge ${sub ? "sub" : ""}`}>
      <ColorDots color={color ?? null} />
      {sub ? lineCode : `Ligne ${lineCode}`}
      {!sub && variant && variant !== "Unique" && <small>{variant}</small>}
    </span>
  );
}

export const Flag = ({ tone = "b-neutral", children }: { tone?: string; children: ReactNode }) =>
  <span className={`badge ${tone}`}>{children}</span>;
