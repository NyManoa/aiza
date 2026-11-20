import { useEffect, useMemo, useState } from "react";

import { useItineraries } from "../../api/queries";
import type { Highlight, Itinerary } from "../../api/types";
import { Alert, ErrorBox } from "../../components/Feedback";
import { Icon } from "../../components/Icon";
import { fmt } from "../../lib/format";
import { useMediaQuery } from "../../lib/useMediaQuery";
import { EndpointField } from "./EndpointField";
import { EndpointInfo } from "./EndpointInfo";
import { applyFilters, DEFAULT_FILTERS, type ItineraryFilters } from "./filters";
import { ItineraryCard } from "./ItineraryCard";
import { ItineraryDetail } from "./ItineraryDetail";
import { FiltersPanel, SortTabs } from "./Toolbar";
import { usePlannerParams } from "./usePlannerParams";

const PAGE = 20;
const MODE_TONE = { normal: null, acces_elargi: "warn", approche: "warn" } as const;

export function PlannerPage() {
  const { from, to, maxTransfers, setFrom, setTo, setMax, swap } = usePlannerParams();
  const route = useItineraries(from, to, maxTransfers);
  const [filters, setFilters] = useState<ItineraryFilters>(DEFAULT_FILTERS);
  const [selected, setSelected] = useState<number | null>(null);
  const [shown, setShown] = useState(PAGE);
  const wide = useMediaQuery("(min-width: 1024px)");

  const data = route.data;
  const all = useMemo(() => data?.itineraries ?? [], [data]);
  const list = useMemo(() => applyFilters(all, filters), [all, filters]);
  useEffect(() => { setSelected(null); setShown(PAGE); }, [data]);
  useEffect(() => { setShown(PAGE); }, [filters]);

  const current: Itinerary | undefined = list.find((i) => i.id === selected) ?? (wide ? list[0] : undefined);
  const highlights = data?.highlights ?? {};
  const tagsOf = (id: number) => (Object.entries(highlights) as [Highlight, number | null][])
    .filter(([k, v]) => v === id && (k === "recommande" || k === "plus_court")).map(([k]) => k);
  const pruned = data?.pruned ?? {};
  const nPruned = (pruned.va_et_vient ?? 0) + (pruned.detours ?? 0) + (pruned.doublons ?? 0) + (pruned.domines ?? 0);
  const total = Object.values(data?.counts ?? {}).reduce((a, b) => a + b, 0);

  return (
    <>
      <section className="card search-card" aria-label="Recherche d'itinéraire">
        <div className="ep-grid">
          <div className="ep-fields">
            <EndpointField role="from" value={from} onChange={setFrom} />
            <EndpointField role="to" value={to} onChange={setTo} />
          </div>
          <button type="button" className="icon-btn swap-btn" onClick={swap} disabled={!from && !to}
                  title="Inverser départ et arrivée" aria-label="Inverser départ et arrivée">
            <Icon name="swap" />
          </button>
        </div>
        <div className="search-options">
          <div className="opt">
            <span>Correspondances</span>
            <div className="segmented" role="group" aria-label="Nombre maximal de correspondances">
              {[[0, "Direct"], [1, "≤ 1"], [2, "≤ 2"]].map(([k, l]) => (
                <button key={k} type="button" aria-pressed={maxTransfers === k} onClick={() => setMax(k as number)}>{l}</button>
              ))}
            </div>
          </div>
          <div className="opt" aria-live="polite">
            {!from || !to ? "La recherche démarre dès que départ et arrivée sont choisis."
              : route.isFetching ? "Calcul en cours…"
              : data ? `${total} itinéraire${total > 1 ? "s" : ""}${data.direct_km !== null ? ` · ${fmt(data.direct_km, 1)} km à vol d'oiseau` : ""}` : ""}
          </div>
        </div>
      </section>

      {(!from || !to) && <EmptyState />}
      {route.isError && <div className="results"><ErrorBox error={route.error} /></div>}
      {route.isLoading && <div className="results"><div className="skeleton" /><div className="skeleton" /><div className="skeleton" /></div>}

      {data && (
        <section className="results" aria-label="Résultats">
          <div className="ends">
            <EndpointInfo end={data.origin} role="from" defaultOpen={wide} />
            <EndpointInfo end={data.destination} role="to" defaultOpen={wide} />
          </div>
          {(data.messages.length > 0 || nPruned > 0) && (
            <div className="notices">
              {data.messages.map((m) => (
                <Alert key={m} tone={MODE_TONE[data.search_mode] ?? "info"}><Icon name="info" /><span>{m}</span></Alert>
              ))}
              {nPruned > 0 && (
                <p className="t-meta">
                  Écartés automatiquement : {pruned.va_et_vient ?? 0} va-et-vient, {pruned.detours ?? 0} détours,{" "}
                  {pruned.doublons ?? 0} doublons, {pruned.domines ?? 0} trajets dominés.
                </p>
              )}
            </div>
          )}

          <div className="results-grid">
            <div>
              <div className="toolbar">
                <SortTabs value={filters.sort} onChange={(sort) => setFilters((f) => ({ ...f, sort }))} />
                <FiltersPanel value={filters} onChange={setFilters} counts={data.counts} />
              </div>
              {list.length === 0 && <div className="card muted">Aucun itinéraire ne correspond aux filtres.</div>}
              <div className="itin-list">
                {list.slice(0, shown).map((it) => {
                  const isSel = current?.id === it.id;
                  return (
                    <div key={it.id}>
                      <ItineraryCard it={it} selected={isSel} tags={tagsOf(it.id)}
                                     onSelect={() => setSelected(isSel && !wide ? null : it.id)} />
                      {!wide && isSel && (
                        <div className="card inline-detail">
                          <ItineraryDetail it={it} origin={data.origin} destination={data.destination} />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
              {list.length > shown && (
                <div className="more">
                  <button type="button" className="btn" onClick={() => setShown((s) => s + PAGE)}>
                    Afficher plus ({list.length - shown})
                  </button>
                </div>
              )}
            </div>
            {wide && (
              <aside className="card detail-panel" aria-label="Détail de l'itinéraire">
                {current
                  ? <ItineraryDetail it={current} origin={data.origin} destination={data.destination} />
                  : <p className="muted">Aucun itinéraire à afficher.</p>}
              </aside>
            )}
          </div>
        </section>
      )}
    </>
  );
}

function EmptyState() {
  return (
    <section className="empty">
      <div className="empty-illu"><Icon name="route" className="icon" /></div>
      <p className="big">Où allez-vous ?</p>
      <p>Tapez un fokontany, un arrêt (Analakely, 67ha…) ou un pcode, ou parcourez la hiérarchie administrative.</p>
      <div className="tips">
        <div className="tip"><b>Toujours une solution</b>Sans ligne directe, le planificateur propose les arrêts les plus proches et la marche nécessaire.</div>
        <div className="tip"><b>Transparent</b>Chaque rattachement affiche son niveau de confiance ; chaque score est détaillé.</div>
        <div className="tip"><b>Partageable</b>L'adresse de la page contient votre recherche : copiez-la pour la partager.</div>
      </div>
    </section>
  );
}
