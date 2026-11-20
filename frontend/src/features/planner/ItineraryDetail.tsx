import type { CSSProperties, ReactNode } from "react";

import type { Access, EndpointInfo, Itinerary, Leg } from "../../api/types";
import { ConfidenceBadge, Flag, LineBadge } from "../../components/Badges";
import { Icon } from "../../components/Icon";
import { adminLine, fmt } from "../../lib/format";
import { ACCESS_LABEL, kindLabel, SCORE_LABEL } from "../../lib/labels";

const COLOR_VAR: Record<string, string> = { bleu: "var(--c-bleu)", rouge: "var(--c-rouge)", vert: "var(--c-vert)", jaune: "var(--c-jaune)" };
const legColor = (leg: Leg) =>
  COLOR_VAR[(leg.color ?? "").split("-")[0] ?? ""] ?? (leg.zone === "suburbaine" ? "var(--suburban)" : "var(--urban)");

function Step({ kind, dot, line, children, style }: {
  kind: "from" | "to" | "ride" | "walk" | "transfer"; dot: ReactNode; line?: "ride" | "walk" | "plain";
  children: ReactNode; style?: CSSProperties;
}) {
  return (
    <li className="step" style={style}>
      <div className="step-rail">
        <span className={`step-dot ${kind}`}>{dot}</span>
        <span className={`step-line ${line ?? ""}`} />
      </div>
      <div className="step-body">{children}</div>
    </li>
  );
}

function walkText(acc: Access, start: boolean) {
  const target = acc.via_fokontany?.adm4_name;
  const km = `≈ ${fmt(acc.walk_km, 1)} km`;
  return start
    ? `Marcher ${km} jusqu'à l'arrêt « ${acc.place.name} »${target ? ` (${target})` : ""}`
    : `Marcher ${km} depuis l'arrêt « ${acc.place.name} » jusqu'à destination`;
}

export function ItineraryDetail({ it, origin, destination }: { it: Itinerary; origin: EndpointInfo; destination: EndpointInfo }) {
  const rows = Object.entries(it.score_breakdown).filter(([k, v]) => k === "base" || v !== 0);
  const o = it.access.origin, d = it.access.destination;
  return (
    <div>
      <div className="detail-head">
        <div>
          <div className="itin-kind">{kindLabel(it.transfers)} · itinéraire n° {it.id}</div>
          <div className="km">≈ {fmt(it.total_km, 1)} km</div>
        </div>
        {it.walk_km > 6 && <span className="badge b-bad">longue marche</span>}
      </div>
      <div className="detail-sub">
        <span>bus {fmt(it.bus_km, 1)} km</span><span>marche {fmt(it.walk_km, 1)} km</span>
        {it.direct_km !== null && <span>distance directe {fmt(it.direct_km, 1)} km</span>}
      </div>

      <ol className="steps">
        <Step kind="from" dot="A" line={o.walk_km > 0 ? "walk" : "plain"}>
          <div className="step-title">{origin.fokontany.adm4_name}</div>
          <div className="step-meta">{adminLine(origin.fokontany.adm3_name, origin.fokontany.adm2_name)} · <code>{origin.fokontany.adm4_pcode}</code></div>
        </Step>
        {o.walk_km > 0 && (
          <Step kind="walk" dot={<Icon name="walk" />} line="plain">
            <div className="step-title">{walkText(o, true)}</div>
            <div className="step-meta">{ACCESS_LABEL[o.mode]}</div>
          </Step>
        )}
        {it.legs.map((leg, n) => {
          const t = it.transfer_points[n];
          const color = { "--leg-color": legColor(leg) } as CSSProperties;
          return [
            <Step key={`l${n}`} kind="ride" dot={<Icon name="bus" />} line="ride" style={color}>
              <div className="step-title">
                <LineBadge zone={leg.zone} lineCode={leg.line_code} variant={leg.variant} color={leg.color} />
                {leg.headsign && <span>direction {leg.headsign}</span>}
              </div>
              <div className="step-meta">
                Monter à <b>{leg.from.name}</b>, descendre à <b>{leg.to.name}</b>
                {leg.n_segments !== null ? ` · ${leg.n_segments} arrêt(s)` : ""} · ≈ {fmt(leg.km, 1)} km
              </div>
              {(leg.sector || leg.note) && <div className="step-meta">{[leg.sector && `secteur ${leg.sector}`, leg.note].filter(Boolean).join(" · ")}</div>}
              <div className="step-flags">
                {leg.direction === "retour_suppose" && <Flag tone="b-warn">sens retour supposé</Flag>}
                {leg.wrap && <Flag tone="b-warn">passe par le terminus</Flag>}
                {leg.loop && <Flag>circulaire</Flag>}
                {leg.from.virtual && <Flag tone="b-warn">montée en passage (à confirmer)</Flag>}
                {leg.to.virtual && <Flag tone="b-warn">descente en passage (à confirmer)</Flag>}
                {leg.km_unknown > 0 && <Flag>distance partiellement estimée</Flag>}
              </div>
              {leg.stops_known ? (
                <details>
                  <summary>Voir les {leg.stops.length} arrêts</summary>
                  <ol className={`stops${leg.stops.length > 8 ? " many" : ""}`}>
                    {leg.stops.map((s, i) => <li key={i} className={i === 0 || i === leg.stops.length - 1 ? "end" : ""}>{s}</li>)}
                  </ol>
                </details>
              ) : (
                <div className="nostops">
                  Liaison {leg.raw.replace("Primus : ", "").replace(" -> Terminus : ", " → ")} : arrêts intermédiaires non fournis
                  (aucun arrêt inventé){leg.via_mention && ` · mention : passant par ${leg.via_mention}`}.
                </div>
              )}
              {leg.passages.length > 0 && (
                <details>
                  <summary>Fokontany traversés ({leg.passages.length}, estimation)</summary>
                  <div className="step-meta">{leg.passages.join(" · ")}</div>
                </details>
              )}
            </Step>,
            t && (
              <Step key={`t${n}`} kind={t.type === "meme_lieu" ? "transfer" : "walk"}
                    dot={<Icon name={t.type === "meme_lieu" ? "transfer" : "walk"} />} line="plain">
                <div className="step-title">
                  {t.type === "meme_lieu" ? `Correspondance à « ${t.at.name} »` : `Correspondance à pied : « ${t.at.name} » → « ${t.to.name} »`}
                </div>
                <div className="step-meta">
                  {t.type === "meme_lieu" ? "Même point du réseau" : `≈ ${fmt(t.walk_km, 1)} km dans le même fokontany`}
                </div>
              </Step>
            ),
          ];
        })}
        {d.walk_km > 0 && (
          <Step kind="walk" dot={<Icon name="walk" />} line="plain">
            <div className="step-title">{walkText(d, false)}</div>
            <div className="step-meta">{ACCESS_LABEL[d.mode]}</div>
          </Step>
        )}
        <Step kind="to" dot="B">
          <div className="step-title">{destination.fokontany.adm4_name}</div>
          <div className="step-meta">{adminLine(destination.fokontany.adm3_name, destination.fokontany.adm2_name)} · <code>{destination.fokontany.adm4_pcode}</code></div>
        </Step>
      </ol>

      <details className="why disclosure">
        <summary><Icon name="info" /> Pourquoi ce classement ? <span className="chev"><Icon name="chevron" /></span></summary>
        <div className="step-meta" style={{ marginTop: 8 }}>
          Rattachement départ : <ConfidenceBadge status={o.status} confidence={o.confidence} /> · arrivée :{" "}
          <ConfidenceBadge status={d.status} confidence={d.confidence} />
        </div>
        <table>
          <tbody>
            {rows.map(([k, v]) => (
              <tr key={k}><td>{SCORE_LABEL[k] ?? k}</td><td className={`num${v < 0 ? " neg" : ""}`}>{fmt(v, 1)}</td></tr>
            ))}
            <tr><th>Total</th><th className="num">{fmt(it.score, 1)}</th></tr>
          </tbody>
        </table>
        <p className="t-meta" style={{ marginTop: 8 }}>Distances à vol d'oiseau entre arrêts : ordre de grandeur, pas un kilométrage routier.</p>
      </details>
    </div>
  );
}
