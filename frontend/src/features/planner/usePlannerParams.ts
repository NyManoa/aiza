import { useCallback } from "react";
import { useSearchParams } from "react-router";

const PCODE = /^MG\d{11}$/;
const clean = (v: string | null) => (v && PCODE.test(v) ? v : null);

/** État du planificateur dans l'URL (?from=&to=&max=) : partageable, rechargeable, navigable. */
export function usePlannerParams() {
  const [params, setParams] = useSearchParams();
  const from = clean(params.get("from"));
  const to = clean(params.get("to"));
  const maxRaw = Number(params.get("max") ?? 2);
  const maxTransfers = [0, 1, 2].includes(maxRaw) ? maxRaw : 2;

  const update = useCallback((patch: Record<string, string | null>) => {
    setParams((prev) => {
      const next = new URLSearchParams(prev);
      for (const [k, v] of Object.entries(patch)) {
        if (v === null) next.delete(k);
        else next.set(k, v);
      }
      return next;
    }, { replace: true });
  }, [setParams]);

  return {
    from, to, maxTransfers,
    setFrom: (v: string | null) => update({ from: v }),
    setTo: (v: string | null) => update({ to: v }),
    setMax: (n: number) => update({ max: n === 2 ? null : String(n) }),
    swap: () => update({ from: to, to: from }),
  };
}
