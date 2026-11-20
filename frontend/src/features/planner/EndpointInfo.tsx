import type { EndpointInfo as EndpointInfoT } from "../../api/types";
import { ConfidenceBadge, CoverageBadge, LineBadge } from "../../components/Badges";
import { Alert } from "../../components/Feedback";
import { Icon } from "../../components/Icon";
import { adminLine, fmt } from "../../lib/format";
import { ACCESS_LABEL } from "../../lib/labels";

/** Fiche repliable d'une extrémité : desserte, points d'accès, alertes, lignes. */
export function EndpointInfo({ end, role, defaultOpen }: { end: EndpointInfoT; role: "from" | "to"; defaultOpen: boolean }) {
  const f = end.fokontany;
  const access = end.access.slice(0, 6);
  return (
    <details className="card end-card disclosure" open={defaultOpen && end.warnings.length > 0}>
      <summary>
        <span className="head">
          <span className={`ep-marker mini ${role}`} aria-hidden="true">{role === "from" ? "A" : "B"}</span>
          <span className="t">
            <b>{f.adm4_name} {end.warnings.length > 0 && <span className="warn-ic" title="Desserte limitée"><Icon name="warn" /></span>}</b>
            <span className="t-meta">{adminLine(f.adm3_name, f.adm2_name)} · <code>{f.adm4_pcode}</code></span>
          </span>
          <CoverageBadge served={end.served} />
        </span>
        <span className="chev"><Icon name="chevron" /></span>
      </summary>
      <div className="content">
        {end.warnings.map((w) => <Alert key={w} tone="warn"><Icon name="warn" /><span>{w}</span></Alert>)}
        {access.length > 0 && (
          <div>
            <div className="t-meta" style={{ marginBottom: 4 }}>Points d'accès au réseau (les plus pratiques d'abord)</div>
            <ul className="access-list">
              {access.map((a) => (
                <li key={a.place.place_id}>
                  <b>{a.place.name}</b>
                  <span className="t-meta">{ACCESS_LABEL[a.mode]}{a.walk_km > 0 && ` · ${fmt(a.walk_km, 1)} km à pied`}</span>
                  <ConfidenceBadge status={a.status} confidence={a.confidence} />
                </li>
              ))}
            </ul>
            {end.access.length > access.length && <span className="t-meta">+ {end.access.length - access.length} autre(s)</span>}
          </div>
        )}
        {end.lines_here.length > 0 && (
          <div>
            <div className="t-meta" style={{ marginBottom: 4 }}>Lignes accessibles ({end.lines_here.length})</div>
            <div className="lines-here">
              {end.lines_here.slice(0, 16).map((l) => (
                <span key={l.service_id} title={`${l.passage ? "passe par" : "à"} « ${l.place} » : ${l.from} → ${l.to}`}>
                  <LineBadge zone={l.zone} lineCode={l.line_code} variant={l.variant} />
                </span>
              ))}
              {end.lines_here.length > 16 && <span className="t-meta">+ {end.lines_here.length - 16}</span>}
            </div>
          </div>
        )}
      </div>
    </details>
  );
}
