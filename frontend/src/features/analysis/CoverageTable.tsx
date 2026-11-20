import type { CoverageRow } from "../../api/types";
import { fmt } from "../../lib/format";

export const CoverageLegend = () => (
  <div className="legend">
    <span><i style={{ background: "var(--ok)" }} />direct (≥ 2 lignes)</span>
    <span><i style={{ background: "var(--c-jaune)" }} />faible (1 ligne)</span>
    <span><i style={{ background: "var(--c-violet)" }} />traversé (estimé)</span>
    <span><i style={{ background: "var(--suburban)" }} />communal (approx.)</span>
    <span><i style={{ background: "var(--surface-2)", border: "1px solid var(--border)" }} />aucune</span>
  </div>
);

export function CoverageTable({ rows, by }: { rows: CoverageRow[]; by: "adm2_name" | "adm3_name" }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Zone</th><th className="num">Fkt</th><th>Répartition</th><th className="num">Direct</th>
            <th className="num">Faible</th><th className="num">Passage</th><th className="num">Commune</th><th className="num">Aucune</th>
            <th className="num">% fkt desservis</th><th className="num">km²</th><th className="num">% surface</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((d) => {
            const seg = (k: "direct" | "faible" | "passage" | "commune") =>
              <span className={`s-${k}`} style={{ width: `${(100 * d[k]) / d.n_fokontany}%` }} title={`${k} : ${d[k]}`} />;
            return (
              <tr key={(d.adm3_pcode ?? d.adm2_pcode ?? d.adm2_name) + by}>
                <td>{d[by]}{by === "adm3_name" && <><br /><span className="t-meta">{d.adm2_name}</span></>}</td>
                <td className="num">{d.n_fokontany}</td>
                <td style={{ minWidth: 140 }}><span className="bar">{seg("direct")}{seg("faible")}{seg("passage")}{seg("commune")}</span></td>
                <td className="num">{d.direct}</td><td className="num">{d.faible}</td><td className="num">{d.passage}</td>
                <td className="num">{d.commune}</td><td className="num">{d.aucune}</td>
                <td className="num">{fmt(d.pct_fokontany_direct, 1)} %</td>
                <td className="num">{fmt(d.area_sqkm, 1)}</td>
                <td className="num">{fmt(d.pct_area_direct, 1)} %</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
