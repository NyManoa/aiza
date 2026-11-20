const nf = new Map<number, Intl.NumberFormat>();

/** Nombre au format français ; « – » si absent. */
export function fmt(n: number | null | undefined, digits = 2): string {
  if (n === null || n === undefined || Number.isNaN(n)) return "–";
  let f = nf.get(digits);
  if (!f) nf.set(digits, (f = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: digits })));
  return f.format(n);
}

/** « Commune · District » sans doublon (ex. arrondissements : commune = district). */
export const adminLine = (...parts: (string | null | undefined)[]) =>
  parts.filter((p, i, a): p is string => !!p && a.indexOf(p) === i).join(" · ");

export const plural = (n: number, one: string, many = `${one}s`) => (n > 1 ? many : one);
