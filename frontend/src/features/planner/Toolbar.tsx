import { Icon } from "../../components/Icon";
import { DEFAULT_FILTERS, type ItineraryFilters, type SortKey, toggle, type ZoneKind } from "./filters";

const SORTS: [SortKey, string][] = [
  ["recommande", "Recommandé"], ["plus_court", "Plus court"],
  ["moins_de_marche", "Moins de marche"], ["moins_de_correspondances", "Moins de corresp."],
];
const ZONES: [ZoneKind, string][] = [["urbaine", "Urbaine"], ["suburbaine", "Suburbaine"], ["mixte", "Mixte"]];

export function SortTabs({ value, onChange }: { value: SortKey; onChange: (s: SortKey) => void }) {
  return (
    <div className="segmented" role="tablist" aria-label="Trier les itinéraires">
      {SORTS.map(([k, l]) => (
        <button key={k} type="button" role="tab" aria-selected={value === k} onClick={() => onChange(k)}>{l}</button>
      ))}
    </div>
  );
}

function activeCount(f: ItineraryFilters): number {
  const d = DEFAULT_FILTERS;
  return Number(f.transfers.length !== d.transfers.length) + Number(f.zones.length !== d.zones.length)
    + Number(f.minConfidence !== d.minConfidence) + Number(f.publishedDirectionOnly) + Number(f.noWalk)
    + Number(f.publishedStopsOnly);
}

export function FiltersPanel({ value: f, onChange, counts }:
  { value: ItineraryFilters; onChange: (f: ItineraryFilters) => void; counts: Record<string, number> }) {
  const n = activeCount(f);
  const many = Object.entries(counts).filter(([k]) => Number(k) >= 3).reduce((a, [, v]) => a + v, 0);
  return (
    <details className="card filters-panel disclosure">
      <summary>
        <Icon name="filter" /> Filtres {n > 0 && <span className="chip-count">{n}</span>}
        <span className="chev"><Icon name="chevron" /></span>
      </summary>
      <div className="filters-body">
        <fieldset className="filter-group">
          <legend>Correspondances</legend>
          {[0, 1, 2, 3].filter((k) => k < 3 || many > 0).map((k) => (
            <label key={k}>
              <input type="checkbox" checked={f.transfers.includes(k)} onChange={() => onChange({ ...f, transfers: toggle(f.transfers, k) })} />
              {k === 0 ? "Direct" : k === 3 ? "3+ corresp." : `${k} corresp.`}{" "}
              <span className="muted">({k === 3 ? many : counts[String(k)] ?? 0})</span>
            </label>
          ))}
        </fieldset>
        <fieldset className="filter-group">
          <legend>Type de ligne</legend>
          {ZONES.map(([z, l]) => (
            <label key={z}><input type="checkbox" checked={f.zones.includes(z)} onChange={() => onChange({ ...f, zones: toggle(f.zones, z) })} />{l}</label>
          ))}
        </fieldset>
        <fieldset className="filter-group">
          <legend>Fiabilité</legend>
          <select value={f.minConfidence} onChange={(e) => onChange({ ...f, minConfidence: Number(e.target.value) })} aria-label="Confiance minimale">
            <option value={0}>Toute confiance</option>
            <option value={0.5}>Confiance ≥ 0,50</option>
            <option value={0.65}>Confiance ≥ 0,65</option>
            <option value={0.85}>Rattachement exact</option>
          </select>
          <label><input type="checkbox" checked={f.publishedDirectionOnly} onChange={(e) => onChange({ ...f, publishedDirectionOnly: e.target.checked })} />Sens publié</label>
          <label><input type="checkbox" checked={f.publishedStopsOnly} onChange={(e) => onChange({ ...f, publishedStopsOnly: e.target.checked })} />Arrêts publiés</label>
          <label><input type="checkbox" checked={f.noWalk} onChange={(e) => onChange({ ...f, noWalk: e.target.checked })} />Sans marche</label>
        </fieldset>
        {n > 0 && <div><button type="button" className="btn" onClick={() => onChange({ ...DEFAULT_FILTERS, sort: f.sort })}>Réinitialiser</button></div>}
      </div>
    </details>
  );
}
