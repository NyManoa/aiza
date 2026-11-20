import { useEffect, useId, useRef, useState } from "react";

import { useSearch } from "../../api/queries";
import { CoverageBadge } from "../../components/Badges";
import { Icon } from "../../components/Icon";
import { useDebounced } from "../../lib/useDebounced";

interface Props {
  onPick: (code: string) => void;
  onEscape?: () => void;
  autoFocus?: boolean;
  placeholder?: string;
  label: string;
}

/** Recherche par nom de fokontany, nom d'arrêt ou pcode, avec navigation clavier (combobox ARIA). */
export function SearchBox({ onPick, onEscape, autoFocus, placeholder, label }: Props) {
  const [text, setText] = useState("");
  const [open, setOpen] = useState(false);
  const [hl, setHl] = useState(-1);
  const q = useDebounced(text.trim(), 160);
  const { data, isFetching } = useSearch(q);
  const listId = useId();
  const wrap = useRef<HTMLDivElement>(null);
  const items = q.length >= 2 ? (data ?? []) : [];

  useEffect(() => {
    const close = (e: MouseEvent) => { if (!wrap.current?.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);
  useEffect(() => setHl(-1), [q]);

  const pick = (code: string) => {
    onPick(code);
    setText("");
    setOpen(false);
  };

  return (
    <div className="search-wrap" ref={wrap}>
      <span className="search-icon"><Icon name="search" /></span>
      <input
        type="search" value={text} autoComplete="off" autoFocus={autoFocus} aria-label={label}
        placeholder={placeholder ?? "Fokontany, arrêt ou pcode…"}
        role="combobox" aria-expanded={open && items.length > 0} aria-controls={listId} aria-autocomplete="list"
        aria-activedescendant={hl >= 0 ? `${listId}-${hl}` : undefined}
        onChange={(e) => { setText(e.target.value); setOpen(true); }}
        onFocus={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === "Escape") { setOpen(false); onEscape?.(); return; }
          if (!items.length) return;
          if (e.key === "ArrowDown" || e.key === "ArrowUp") {
            e.preventDefault();
            setHl((h) => (h + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length);
          } else if (e.key === "Enter") {
            e.preventDefault();
            const it = items[hl] ?? items[0];
            if (it) pick(it.adm4_pcode);
          }
        }}
      />
      {open && q.length >= 2 && (
        <ul className="suggest" role="listbox" id={listId}>
          {items.length === 0 && <li className="muted">{isFetching ? "Recherche…" : "Aucun résultat"}</li>}
          {items.map((it, i) => (
            <li key={it.adm4_pcode} id={`${listId}-${i}`} role="option" aria-selected={i === hl}
                className={i === hl ? "hl" : ""} onMouseDown={(e) => { e.preventDefault(); pick(it.adm4_pcode); }}>
              <span style={{ minWidth: 0 }}>
                <span className="s-main">{it.adm4_name}</span><br />
                <span className="s-sub">
                  {it.adm3_name} · {it.adm2_name}{it.adm1_pcode !== "MG11" && ` · ${it.adm1_name}`}
                  {it.via_place && <> · arrêt « {it.via_place} »</>}
                </span>
              </span>
              <CoverageBadge served={it.served} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
