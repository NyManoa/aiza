import json

import pandas as pd
import pytest

from planner import rules


@pytest.fixture(scope="module")
def t(settings):
    d = settings.tables_dir
    return {n: pd.read_csv(d / f"{n}.csv") for n in
            ("lines", "suburban_links", "places", "place_admin_matches", "admin4", "admin3")}


def test_counts_match_corpus_and_referential(t):
    assert int((t["lines"].zone == "urbaine").sum()) == 58
    assert len(t["suburban_links"]) == 85                       # 72 + ligne I (9) + ligne J (4)
    assert sorted(t["suburban_links"].line_id.unique()) == ["S-A", "S-B", "S-D", "S-E", "S-F", "S-G", "S-H", "S-I", "S-J"]
    assert len(t["admin4"]) == 17465
    assert int((t["admin4"].adm1_pcode == "MG11").sum()) == 1660
    assert int((t["admin3"].adm1_pcode == "MG11").sum()) == 139


def test_every_place_has_public_status(t):
    assert set(t["places"].match_status) <= set(rules.PUBLIC_STATUSES)
    assert set(t["place_admin_matches"].place_id) == set(t["places"].place_id)


def _fk(t, pid):
    m = t["place_admin_matches"]
    return set(m[m.place_id == pid].adm4_name.dropna())


def test_known_matches(t):
    m = t["place_admin_matches"]
    assert _fk(t, "analakely") == {"Antanimalalaka Analakely"}
    assert "Ankerana Ankadindramamy" in _fk(t, "ankerana")        # niveau 1 avant homonyme rural
    assert _fk(t, "homi") == {"Soavinandriana"}                     # table manuelle
    assert _fk(t, "ankaraobato_ifarihy") == {"Ifarihy"}             # commune + fokontany
    assert _fk(t, "mahatsinjo_alasora") == {"Mahatsinjo"}           # fokontany + commune
    assert m.set_index("place_id").loc["imerintsiatosika", "adm1_pcode"] == "MG13"
    nord = m[m.place_id == "ambatofotsy_nord"].adm3_name.iloc[0]
    sud = m[m.place_id == "ambatofotsy_sud"].adm3_name.iloc[0]
    assert nord != sud                                              # filtre directionnel


@pytest.mark.parametrize("pid", ["meteo", "cnaps", "mausolee"])
def test_landmarks_without_evidence_stay_unresolved(t, pid):
    assert t["places"].set_index("place_id").match_status[pid] == "non_resolu"


def test_route_consistency_and_user_clarification(t):
    assert _fk(t, "ambodivona") <= {"Ambodivona Ankadifotsy", "Mandialaza Ambodivona"}   # cohérence voisins
    assert "Ambodivona Ankadifotsy" in _fk(t, "st_antoine_ambodivona")                    # précision du corpus
    assert _fk(t, "alakamisy_antanimarina") == {"Antanimarina"}                           # préfixe jour de marché


def test_geometry(settings):
    geo = pd.read_csv(settings.tables_dir / "place_geometry.csv").set_index("place_id")
    assert geo.loc["meteo", "quality"] == "estimee_voisins"
    cor = pd.read_csv(settings.tables_dir / "line_corridors.csv")
    assert set(cor.source) <= {"corridor_estime", "declare"}
    assert not cor.service_id.str.startswith("S-").any() or set(cor[cor.service_id.str.startswith("S-")].source) == {"declare"}


def test_suburban_links_have_no_intermediate_stops(settings):
    net = json.loads(settings.network_json.read_text(encoding="utf-8"))
    subs = [s for s in net["services"] if s["zone"] == "suburbaine"]
    assert len(subs) == 85
    assert all(len(s["stops"]) == 2 and not s["stops_known"] for s in subs)


def test_no_nan_in_json_outputs(settings):
    def boom(c):
        raise AssertionError(f"{c} dans un JSON")
    for p in (settings.network_json, settings.stats_json):
        json.loads(p.read_text(encoding="utf-8"), parse_constant=boom)
