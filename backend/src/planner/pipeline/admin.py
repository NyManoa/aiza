"""Étape 1a — Extraction du référentiel administratif.

Produit (data/output/) :
  admin1.csv … admin4.csv     structure nationale allégée (noms, pcodes, parents, area_sqkm)
  admin4_analamanga.csv       périmètre Analamanga (+ coordonnées du centroïde, niveau de périmètre)
  fokontany_neighbors.csv     voisinage fokontany <-> fokontany (frontière commune, mdg_adminlines)
  old_provinces.csv           correspondance régions <-> anciennes provinces
  admin_capitals.csv          chefs-lieux
"""
from __future__ import annotations

import pandas as pd

from planner import rules
from planner.settings import get_settings


def _tier(adm2: str) -> int:
    if adm2 in rules.TIER1_DISTRICTS:
        return 1
    if adm2 in rules.TIER2_DISTRICTS:
        return 2
    return 3


def build() -> dict[str, int]:
    out = get_settings().tables_dir
    out.mkdir(parents=True, exist_ok=True)
    xl = pd.read_excel(get_settings().admin_xlsx, sheet_name=None)

    a1 = xl["mdg_admin1"][["adm1_pcode", "adm1_name", "area_sqkm"]].sort_values("adm1_name").copy()
    a2 = xl["mdg_admin2"][["adm2_pcode", "adm2_name", "adm1_pcode", "adm1_name", "area_sqkm"]].copy()
    a3 = xl["mdg_admin3"][["adm3_pcode", "adm3_name", "adm2_pcode", "adm2_name", "adm1_pcode", "adm1_name", "area_sqkm"]].copy()
    a4 = xl["mdg_admin4"][["adm4_pcode", "adm4_name", "adm3_pcode", "adm3_name", "adm2_pcode", "adm2_name",
                           "adm1_pcode", "adm1_name", "area_sqkm"]].copy()

    old = xl["mgd_op_adm1_old_names_pcodes"][["adm1_pcode", "adm1_en", "old_provin", "prov_code"]]
    a1 = a1.merge(old[["adm1_pcode", "old_provin"]], on="adm1_pcode", how="left")

    pts = xl["mdg_adminpoints"]
    p4 = pts[pts.admin_level == 4][["adm4_pcode", "x_coord", "y_coord"]].rename(columns={"x_coord": "lon", "y_coord": "lat"})
    p3 = pts[pts.admin_level == 3][["adm3_pcode", "x_coord", "y_coord"]].rename(columns={"x_coord": "lon", "y_coord": "lat"})
    a4 = a4.merge(p4.drop_duplicates("adm4_pcode"), on="adm4_pcode", how="left")
    a3 = a3.merge(p3.drop_duplicates("adm3_pcode"), on="adm3_pcode", how="left")

    for df, cols in ((a1, ["area_sqkm"]), (a2, ["area_sqkm"]), (a3, ["area_sqkm"]), (a4, ["area_sqkm"])):
        for c in cols:
            df[c] = df[c].round(4)

    a1.to_csv(out / "admin1.csv", index=False)
    a2.sort_values(["adm1_pcode", "adm2_name"]).to_csv(out / "admin2.csv", index=False)
    a3.sort_values(["adm2_pcode", "adm3_name"]).to_csv(out / "admin3.csv", index=False)
    a4.sort_values(["adm3_pcode", "adm4_name"]).to_csv(out / "admin4.csv", index=False)

    ana = a4[a4.adm1_pcode == rules.ANALAMANGA].copy()
    ana["tier"] = ana.adm2_pcode.map(_tier)
    ana.sort_values(["adm2_pcode", "adm3_name", "adm4_name"]).to_csv(out / "admin4_analamanga.csv", index=False)

    # Voisinage : deux fokontany partageant un segment de frontière (gauche/droite).
    lines = xl["mdg_adminlines"]
    # Tous les niveaux 1..4 portent des pcodes de fokontany : une frontière de niveau 3 sépare aussi deux fokontany
    # (de communes différentes). Le niveau 99 (limite extérieure) n'a pas de voisin.
    l4 = lines[lines.adm_level.isin([1, 2, 3, 4])].dropna(subset=["right_pcod", "left_pcod"])
    ana_codes = set(ana.adm4_pcode)
    l4 = l4[l4.right_pcod.isin(ana_codes) & l4.left_pcod.isin(ana_codes)]
    pairs = {tuple(sorted((a, b))) for a, b in zip(l4.right_pcod, l4.left_pcod, strict=True) if a != b}
    nb = pd.DataFrame(sorted(pairs), columns=["adm4_pcode_a", "adm4_pcode_b"])
    nb.to_csv(out / "fokontany_neighbors.csv", index=False)

    old.to_csv(out / "old_provinces.csv", index=False)
    caps = xl["mdg_admincapitals"][["adm_p_lvl", "name", "x_coord", "y_coord", "adm2_pcode", "adm1_pcode"]]
    caps.to_csv(out / "admin_capitals.csv", index=False)

    return {
        "regions": len(a1), "districts": len(a2), "communes": len(a3), "fokontany": len(a4),
        "districts_analamanga": int((a2.adm1_pcode == rules.ANALAMANGA).sum()),
        "communes_analamanga": int((a3.adm1_pcode == rules.ANALAMANGA).sum()),
        "fokontany_analamanga": len(ana),
        "fokontany_sans_coord": int(ana.lat.isna().sum()),
        "paires_voisines": len(nb),
    }


if __name__ == "__main__":
    for k, v in build().items():
        print(f"{k:28s} {v}")
