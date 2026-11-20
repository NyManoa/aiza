import { fmt } from "../lib/format";

export function BarRow({ label, value, max, title, warn }: {
  label: string; value: number; max: number; title?: string; warn?: boolean;
}) {
  return (
    <div className="bar-row">
      <span className="lbl" title={title ?? label}>{label}{warn && " ⚠"}</span>
      <span className="bar"><span className="s-one" style={{ width: `${max ? (100 * value) / max : 0}%` }} /></span>
      <span className="num">{fmt(value, 0)}</span>
    </div>
  );
}

export function BarList({ entries }: { entries: [string, number][] }) {
  const max = Math.max(0, ...entries.map(([, v]) => v));
  return <>{entries.map(([k, v]) => <BarRow key={k} label={k} value={v} max={max} />)}</>;
}
