import { useMemo, useState } from "react";

import { useLines, usePlaces } from "../../api/queries";
import type { Service, Zone } from "../../api/types";
import { ColorDots, LineBadge } from "../../components/Badges";
import { ErrorBox, Loading } from "../../components/Feedback";
import { Icon } from "../../components/Icon";
import { fmt } from "../../lib/format";
import { useDebounced } from "../../lib/useDebounced";

type ZoneFilter = "all" | Zone;

export default function NetworkPage() {
  const lines = useLines();
  const places = usePlaces();
  const [text, setText] = useState("");
  const [zone, setZone] = useState<ZoneFilter>("all");
  const q = useDebounced(text.trim().toLowerCase(), 150);

  const unresolved = useMemo(
    () => new Set((places.data ?? []).filter((p) => p.match_status === "non_resolu").map((p) => p.name)), [places.data]);
  const byLine = useMemo(() => {
    const m = new Map<string, Service[]>();
    for (const s of lines.data?.services ?? []) m.set(s.line_id, [...(m.get(s.line_id) ?? []), s]);
    return m;
  }, [lines.data]);

  if (lines.isLoading) return <Loading />;
  if (lines.error || !lines.data) return <ErrorBox error={lines.error} />;

  const visible = lines.data.lines.filter((l) => {
    if (zone !== "all" && l.zone !== zone) return false;
    if (!q) return true;
    const svcs = byLine.get(l.line_id) ?? [];
    return `ligne ${l.line_code} ${svcs.map((s) => s.stops_named.flat().join(" ")).join(" ")}`.toLowerCase().includes(q);
  });
  const nUrb = lines.data.lines.filter((l) => l.zone === "urbaine").length;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Lignes du réseau</h1>
          <p>{nUrb} lignes urbaines et {lines.data.lines.length - nUrb} lignes suburbaines (liaisons Primus → Terminus).</p>
        </div>
      </div>
      <div className="net-toolbar">
        <div className="search-wrap">
          <span className="search-icon"><Icon name="search" /></span>
          <input type="search" value={text} onChange={(e) => setText(e.target.value)}
                 placeholder="Ligne ou arrêt (ex. 194, Ligne F, Météo)…" aria-label="Filtrer les lignes" />
        </div>
        <div className="segmented" role="group" aria-label="Type de ligne">
          {([["all", "Toutes"], ["urbaine", "Urbaines"], ["suburbaine", "Suburbaines"]] as [ZoneFilter, string][]).map(([k, l]) => (
            <button key={k} type="button" aria-pressed={zone === k} onClick={() => setZone(k)}>{l}</button>
          ))}
        </div>
      </div>
      <p className="t-meta" style={{ margin: "0 0 12px" }}>
        {visible.length} ligne(s) · <span className="stopchip unres">en rouge</span> lieu non rattaché à un fokontany ·
        « A / B » arrêts alternatifs au même rang.
      </p>
      {visible.length === 0 && <div className="card muted">Aucune ligne ne correspond.</div>}
      <div className="line-list">
        {visible.map((l) => {
          const svcs = byLine.get(l.line_id) ?? [];
          const sub = l.zone === "suburbaine";
          const first = svcs[0];
          const ends = first ? `${first.stops_named[0]?.join(" / ")} → ${first.stops_named[first.stops_named.length - 1]?.join(" / ")}` : "";
          return (
            <details key={l.line_id} className="card line-card disclosure" open={!!q}>
              <summary>
                <LineBadge zone={l.zone} lineCode={l.line_code} />
                <span className="ends-txt">
                  {sub ? `${svcs.length} liaisons` : `${svcs.length} variante${svcs.length > 1 ? "s" : ""} · ${ends}`}
                  {l.note && ` · ${l.note}`}
                </span>
                <span className="chev"><Icon name="chevron" /></span>
              </summary>
              <div className="line-body">
                {svcs.map((s) => (
                  <div key={s.id} className="variant">
                    {!sub && (
                      <div className="vlabel">
                        <ColorDots color={s.color} /> {s.label}{s.sector && ` · ${s.sector}`}
                        {s.loop && <span className="badge b-neutral">circulaire</span>}
                        {s.length_km > 0 && <span className="t-meta">≈ {fmt(s.length_km, 1)} km</span>}
                      </div>
                    )}
                    <div>
                      {s.stops_named.map((pos, i) => (
                        <span key={i}>
                          {i > 0 && (sub ? " → " : " – ")}
                          {pos.map((name, j) => (
                            <span key={j}>{j > 0 && " / "}<span className={`stopchip${unresolved.has(name) ? " unres" : ""}`}>{name}</span></span>
                          ))}
                        </span>
                      ))}
                      {s.via_mention && <span className="t-meta"> (passant par {s.via_mention})</span>}
                    </div>
                    {s.corridor_named.some((c) => c.length > 0) && (
                      <details className="corridor">
                        <summary>Fokontany traversés ({new Set(s.corridor_named.flat().map((c) => c.adm4_pcode)).size})</summary>
                        {s.corridor_named.map((seg, i) => seg.length > 0 && (
                          <div key={i}>
                            {s.stops_named[i]?.join(" / ")} → {s.stops_named[i + 1]?.join(" / ")} :{" "}
                            {seg.map((c) => `${c.name}${c.source === "declare" ? "" : "*"}`).join(", ")}
                          </div>
                        ))}
                        <div>* estimé (plus court chemin de voisinage) — à confirmer.</div>
                      </details>
                    )}
                  </div>
                ))}
              </div>
            </details>
          );
        })}
      </div>
    </>
  );
}
