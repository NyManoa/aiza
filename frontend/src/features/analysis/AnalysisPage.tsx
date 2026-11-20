import { useStats } from "../../api/queries";
import type { MatchStatus } from "../../api/types";
import { ConfidenceBadge } from "../../components/Badges";
import { BarList, BarRow } from "../../components/Bars";
import { ErrorBox, Loading } from "../../components/Feedback";
import { fmt } from "../../lib/format";
import { STATUS_LABEL } from "../../lib/labels";
import { CoverageLegend, CoverageTable } from "./CoverageTable";

const ST_ORDER: MatchStatus[] = ["exact_fokontany", "sous_chaine_fokontany", "commune", "repere_ou_variante", "non_resolu"];
const ST_CONF: Partial<Record<MatchStatus, number>> = {
  exact_fokontany: 1, sous_chaine_fokontany: 0.75, commune: 0.5, repere_ou_variante: 0.5, non_resolu: 0,
};

export default function AnalysisPage() {
  const { data: s, isLoading, error } = useStats();
  if (isLoading) return <Loading />;
  if (error || !s) return <ErrorBox error={error} />;
  const { matching: m, network: n, coverage: c } = s;
  const cv = c.by_coverage_core;
  const maxSt = Math.max(...Object.values(m.by_status_occurrences));
  const maxL = n.top_nodes_by_lines[0]?.n_lines ?? 1;
  const rings = Object.entries(c.rings_distribution_core)
    .map(([k, v]): [string, number] => [k === "0" ? "desservi" : /^\d+$/.test(k) ? `${k} voisin(s)` : k, v]);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Analyse & couverture</h1>
          <p>Rattachement des lieux, nœuds du réseau et desserte des fokontany d'Analamanga.</p>
        </div>
      </div>
      <div className="kpis">
        <Kpi v={n.urban_lines} l={`lignes urbaines · ${n.urban_variants} variantes`} />
        <Kpi v={n.suburban_links} l={`liaisons suburbaines (${n.suburban_groups} lignes A–H)`} />
        <Kpi v={m.n_places} l={`lieux uniques · ${fmt(m.resolved_places_pct, 1)} % rattachés`} />
        <Kpi v={`${fmt(m.resolved_occurrences_pct, 1)} %`} l={`des ${m.n_occurrences} passages rattachés`} />
        <Kpi v={n.transfer_nodes} l="nœuds de correspondance (≥ 2 lignes)" />
        <Kpi v={`${(cv.direct ?? 0) + (cv.faible ?? 0)} / ${c.n_core}`} l="fokontany du cœur desservis directement" />
        <Kpi v={cv.passage ?? 0} l="fokontany du cœur seulement traversés (estimé)" />
        <Kpi v={`${fmt(n.network_length_km, 0)} km`} l="longueur cumulée des variantes urbaines (vol d'oiseau)" />
      </div>

      <div className="grid2">
        <div className="card">
          <h2>Rattachement lieux ↔ fokontany</h2>
          <div className="table-wrap tall"><table>
            <thead><tr><th>Statut</th><th className="num">Lieux</th><th className="num">Passages</th><th style={{ width: "40%" }} /></tr></thead>
            <tbody>
              {ST_ORDER.map((k) => (
                <tr key={k}>
                  <td><ConfidenceBadge status={k} label={STATUS_LABEL[k]} confidence={ST_CONF[k]} showValue={false} /></td>
                  <td className="num">{m.by_status_places[k]}</td>
                  <td className="num">{m.by_status_occurrences[k]}</td>
                  <td><span className="bar"><span className="s-one" style={{ width: `${(100 * (m.by_status_occurrences[k] ?? 0)) / maxSt}%` }} /></span></td>
                </tr>
              ))}
            </tbody>
          </table></div>
          <h3>Distribution des niveaux de confiance (lieux)</h3>
          <BarList entries={Object.entries(m.confidence_distribution)} />
        </div>
        <div className="card">
          <h2>Nœuds principaux (lignes distinctes)</h2>
          <div className="table-wrap">
            {n.top_nodes_by_lines.map((t) => (
              <BarRow key={t.place_id} label={t.name} value={t.n_lines} max={maxL} warn={t.match_status === "non_resolu"} />
            ))}
          </div>
          <p className="t-meta">⚠ = repère non rattaché à un fokontany (reste un nœud de correspondance valide).
            Composantes connexes du graphe : {n.components.join(", ")} nœuds.</p>
          <h3>Géométrie</h3>
          <p className="t-meta">
            Coordonnées des lieux : {Object.entries(n.coord_quality).map(([k, v]) => `${v} ${k.replace("_", " ")}`).join(" · ")}.<br />
            Fokontany traversés : {n.corridor_segments.estimes} tronçons estimés, {n.corridor_segments.declares} déclarés,{" "}
            {n.corridor_segments.fokontany_distincts} fokontany distincts
            (à valider dans <code>backend/data/reference/line_fokontany.csv</code>).
          </p>
        </div>
      </div>

      <section className="card section">
        <h2>Couverture par district / arrondissement (Analamanga)</h2>
        <CoverageLegend />
        <CoverageTable rows={c.by_district} by="adm2_name" />
      </section>
      <section className="card section">
        <h2>Couverture par commune — Renivohitra et périphérie</h2>
        <CoverageLegend />
        <CoverageTable rows={c.by_commune_core} by="adm3_name" />
      </section>

      <div className="grid2">
        <div className="card">
          <h2>Lignes par fokontany (cœur, rattachement direct)</h2>
          <BarList entries={Object.entries(c.lines_per_fokontany_distribution_core)} />
          <h3>Distance au réseau (anneaux de voisinage, cœur)</h3>
          <BarList entries={rings} />
        </div>
        <div className="card">
          <h2>Fokontany les mieux desservis</h2>
          <div className="table-wrap tall"><table>
            <thead><tr><th>Fokontany</th><th>Commune</th><th className="num">Lignes</th><th>Rattachement</th></tr></thead>
            <tbody>
              {c.top_fokontany_by_lines.map((f) => (
                <tr key={f.adm4_pcode}>
                  <td>{f.adm4_name}<br /><code>{f.adm4_pcode}</code></td><td>{f.adm3_name}</td>
                  <td className="num">{f.n_lines_direct}</td>
                  <td><ConfidenceBadge status={f.best_status} confidence={f.best_confidence} /></td>
                </tr>
              ))}
            </tbody>
          </table></div>
        </div>
      </div>

      <div className="grid2">
        <div className="card">
          <h2>Renivohitra : fokontany sans desserte directe ({c.unserved_urban.length})</h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Fokontany</th><th>Arrondissement</th><th>Desserte</th><th className="num">Voisins jusqu'au réseau</th></tr></thead>
              <tbody>
                {c.unserved_urban.map((f) => (
                  <tr key={f.adm4_pcode}>
                    <td>{f.adm4_name}<br /><code>{f.adm4_pcode}</code></td><td>{f.adm3_name}</td>
                    <td>{f.coverage === "commune" ? <span className="badge b-warn">communale</span> : <span className="badge b-bad">aucune</span>}</td>
                    <td className="num">{f.rings_to_network ?? "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="card">
          <h2>Plus grands fokontany non desservis (cœur)</h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Fokontany</th><th>Commune</th><th className="num">km²</th><th className="num">Voisins jusqu'au réseau</th></tr></thead>
              <tbody>
                {c.unserved_core_largest.map((f) => (
                  <tr key={f.adm4_pcode}>
                    <td>{f.adm4_name}</td><td>{f.adm3_name}</td><td className="num">{fmt(f.area_sqkm, 2)}</td>
                    <td className="num">{f.rings_to_network ?? "> 6"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="grid2">
        <div className="card">
          <h2>Faible desserte (1 seule ligne, cœur)</h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Fokontany</th><th>Commune</th><th>Rattachement</th></tr></thead>
              <tbody>
                {c.low_service_core.map((f) => (
                  <tr key={f.adm4_pcode}><td>{f.adm4_name}</td><td>{f.adm3_name}</td><td>{STATUS_LABEL[f.best_status]}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="card">
          <h2>Lieux non résolus — à compléter ({m.unresolved.length})</h2>
          <p className="t-meta">À renseigner dans <code>backend/data/reference/manual_places.csv</code>, puis relancer le pipeline.</p>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Lieu</th><th className="num">Passages</th><th className="num">Lignes</th><th>Rôle</th></tr></thead>
              <tbody>
                {m.unresolved.map((u) => (
                  <tr key={u.place_id}><td>{u.name}</td><td className="num">{u.occurrences}</td><td className="num">{u.n_lines}</td><td>{u.roles}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}

const Kpi = ({ v, l }: { v: string | number; l: string }) => (
  <div className="card kpi"><div className="v">{v}</div><div className="l">{l}</div></div>
);
