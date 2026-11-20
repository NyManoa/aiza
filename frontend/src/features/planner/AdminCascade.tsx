import { useEffect, useState } from "react";

import { useCommunes, useDistricts, useFokontanyList, useRegions } from "../../api/queries";
import type { FokontanyLabel } from "../../api/types";
import { COVERAGE_GLYPH } from "../../lib/labels";

interface Props {
  value: string | null;
  selected: FokontanyLabel | undefined;   // hiérarchie du fokontany sélectionné (pour synchroniser)
  onChange: (code: string | null) => void;
  defaultRegion: string;
}

/** Sélecteur en cascade Région -> District/Arrondissement -> Commune -> Fokontany. */
export function AdminCascade({ value, selected, onChange, defaultRegion }: Props) {
  const [region, setRegion] = useState<string | null>(defaultRegion);
  const [district, setDistrict] = useState<string | null>(null);
  const [commune, setCommune] = useState<string | null>(null);

  // Aligne la cascade sur un fokontany choisi ailleurs (recherche, inversion, URL).
  useEffect(() => {
    if (!selected) return;
    setRegion(selected.adm1_pcode);
    setDistrict(selected.adm2_pcode);
    setCommune(selected.adm3_pcode);
  }, [selected]);

  const regions = useRegions();
  const districts = useDistricts(region);
  const communes = useCommunes(district);
  const fokontany = useFokontanyList(commune);

  // Une seule commune (cas des arrondissements) : sélection automatique.
  useEffect(() => {
    const only = communes.data?.length === 1 ? communes.data[0] : undefined;
    if (only && !commune) setCommune(only.pcode);
  }, [communes.data, commune]);

  return (
    <div className="cascade">
      <label>Région
        <select value={region ?? ""} onChange={(e) => {
          setRegion(e.target.value || null); setDistrict(null); setCommune(null); onChange(null);
        }}>
          <option value="">— Région —</option>
          {regions.data?.map((r) => (
            <option key={r.pcode} value={r.pcode}>{r.name}{r.old_province ? ` (prov. ${r.old_province})` : ""}</option>
          ))}
        </select>
      </label>
      <label>District / Arrondissement
        <select value={district ?? ""} disabled={!districts.data?.length} onChange={(e) => {
          setDistrict(e.target.value || null); setCommune(null); onChange(null);
        }}>
          <option value="">— District / Arrondissement —</option>
          {districts.data?.map((d) => <option key={d.pcode} value={d.pcode}>{d.name}</option>)}
        </select>
      </label>
      <label>Commune
        <select value={commune ?? ""} disabled={!communes.data?.length} onChange={(e) => {
          setCommune(e.target.value || null); onChange(null);
        }}>
          <option value="">— Commune —</option>
          {communes.data?.map((c) => <option key={c.pcode} value={c.pcode}>{c.name}</option>)}
        </select>
      </label>
      <label>Fokontany
        <select value={value ?? ""} disabled={!fokontany.data?.length} onChange={(e) => onChange(e.target.value || null)}>
          <option value="">
            {fokontany.data ? `— Fokontany (${fokontany.data.length}) · ● desservi ◐ communal ○ aucun —` : "— Fokontany —"}
          </option>
          {fokontany.data?.map((f) => (
            <option key={f.pcode} value={f.pcode}>{COVERAGE_GLYPH[f.served.coverage]} {f.name}</option>
          ))}
        </select>
      </label>
    </div>
  );
}
