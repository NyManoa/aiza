import { useState } from "react";

import { useFokontany } from "../../api/queries";
import { CoverageBadge } from "../../components/Badges";
import { Icon } from "../../components/Icon";
import { adminLine } from "../../lib/format";
import { AdminCascade } from "./AdminCascade";
import { SearchBox } from "./SearchBox";

interface Props {
  role: "from" | "to";
  value: string | null;
  onChange: (code: string | null) => void;
}

const TEXT = {
  from: { label: "Départ", marker: "A", placeholder: "Fokontany, arrêt ou pcode de départ" },
  to: { label: "Arrivée", marker: "B", placeholder: "Fokontany, arrêt ou pcode d'arrivée" },
};

/** Champ d'extrémité : recherche d'abord, hiérarchie administrative en option. */
export function EndpointField({ role, value, onChange }: Props) {
  const t = TEXT[role];
  const detail = useFokontany(value);
  const [editing, setEditing] = useState(false);
  const [browse, setBrowse] = useState(false);
  const f = value ? detail.data?.fokontany : undefined;
  const showSearch = !value || editing;

  return (
    <div className="ep-field">
      <span className={`ep-marker ${role}`} aria-hidden="true">{t.marker}</span>
      <div className="ep-body">
        <div className="ep-label" id={`${role}-label`}>{t.label}</div>
        {showSearch ? (
          <SearchBox label={t.label} placeholder={t.placeholder} autoFocus={editing}
                     onPick={(c) => { onChange(c); setEditing(false); }} onEscape={() => setEditing(false)} />
        ) : (
          <div className="ep-selected" aria-labelledby={`${role}-label`}>
            <button type="button" className="grow" onClick={() => setEditing(true)} title="Changer">
              <span className="name">{f?.adm4_name ?? "Chargement…"}</span>
              <span className="sub">
                {detail.data && <CoverageBadge served={detail.data.served} />}{" "}
                {f ? adminLine(f.adm3_name, f.adm2_name) : value}
              </span>
            </button>
            <button type="button" className="ep-clear" onClick={() => onChange(null)} aria-label={`Effacer ${t.label.toLowerCase()}`}>
              <Icon name="close" />
            </button>
          </div>
        )}
        <div className="ep-tools">
          <button type="button" className="btn btn-ghost small" onClick={() => setBrowse((b) => !b)} aria-expanded={browse}>
            <Icon name="tree" /> Parcourir la hiérarchie administrative
          </button>
        </div>
        {browse && (
          <AdminCascade value={value} selected={f} defaultRegion="MG11"
                        onChange={(c) => { onChange(c); if (c) setBrowse(false); }} />
        )}
      </div>
    </div>
  );
}
