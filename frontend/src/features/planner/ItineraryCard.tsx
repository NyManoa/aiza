import type { Highlight, Itinerary } from "../../api/types";
import { Flag, LineBadge } from "../../components/Badges";
import { Icon } from "../../components/Icon";
import { fmt } from "../../lib/format";
import { HIGHLIGHT_LABEL, kindLabel } from "../../lib/labels";

interface Props { it: Itinerary; selected: boolean; onSelect: () => void; tags: Highlight[] }

const Walk = ({ km }: { km: number }) => (
  <span className="walk-chip" title="Marche"><Icon name="walk" />{fmt(km, 1)} km</span>
);

export function ItineraryCard({ it, selected, onSelect, tags }: Props) {
  const first = it.legs[0];
  const last = it.legs[it.legs.length - 1];
  const wo = it.access.origin.walk_km, wd = it.access.destination.walk_km;
  return (
    <button type="button" className={`itin${selected ? " sel" : ""}`} onClick={onSelect} aria-pressed={selected}
            aria-label={`${kindLabel(it.transfers)}, environ ${fmt(it.total_km, 1)} kilomètres`}>
      <div className="itin-top">
        <div className="itin-tags">
          {tags.map((t) => <span key={t} className={`hl-tag hl-${t}`}>{HIGHLIGHT_LABEL[t]}</span>)}
          <span className="itin-kind">{kindLabel(it.transfers)}</span>
        </div>
        <span className="itin-km">≈ {fmt(it.total_km, 1)} <small>km</small></span>
      </div>
      <div className="itin-chain">
        {wo > 0 && <><Walk km={wo} /><span className="chain-sep">›</span></>}
        {it.legs.map((leg, i) => (
          <span key={leg.service_id + i} className="row" style={{ gap: 6 }}>
            {i > 0 && <span className="chain-sep">›</span>}
            <LineBadge zone={leg.zone} lineCode={leg.line_code} variant={leg.variant} color={leg.color} />
          </span>
        ))}
        {wd > 0 && <><span className="chain-sep">›</span><Walk km={wd} /></>}
      </div>
      <div className="itin-route">
        {first?.from.name}
        {it.transfer_points.map((t, i) => (
          <span key={i}> → {t.at.name}{t.type !== "meme_lieu" && <> ⇢ {t.to.name}</>}</span>
        ))}
        {" → "}{last?.to.name}
      </div>
      <div className="itin-foot">
        {it.walk_km > 0 && <Flag tone={it.walk_km > 6 ? "b-bad" : "b-neutral"}>marche {fmt(it.walk_km, 1)} km</Flag>}
        {it.has_reverse && <Flag tone="b-warn">sens retour supposé</Flag>}
        {it.has_passage && <Flag tone="b-warn">accès en passage</Flag>}
        {it.zones.includes("suburbaine") && <Flag>suburbain</Flag>}
        {it.confidence_min < 0.6 && <Flag tone="b-warn">rattachement approximatif</Flag>}

      </div>
    </button>
  );
}
