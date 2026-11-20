import pytest

from planner.engine import NotFoundError


def test_direct_route_ranked_first(analakely_itaosy):
    r = analakely_itaosy
    assert r["counts"].get("0", 0) > 0
    best = r["itineraries"][0]
    assert best["transfers"] == 0 and best["legs"][0]["line_code"] == "133"
    scores = [i["score"] for i in r["itineraries"]]
    assert scores == sorted(scores, reverse=True)


def test_score_breakdown_sums(analakely_itaosy):
    for it in analakely_itaosy["itineraries"]:
        assert sum(it["score_breakdown"].values()) == pytest.approx(it["score"], abs=0.05)


def test_no_dominated_itineraries(analakely_itaosy):
    its = analakely_itaosy["itineraries"]
    direct = [set(i["line_ids"]) for i in its if i["transfers"] == 0]
    for it in its:
        if it["transfers"]:
            assert not any(s <= set(it["line_ids"]) for s in direct)


def test_loop_variant_never_reversed(service):
    loops = {i for i, s in enumerate(service.repo.services) if s["loop"]}
    for m in service.planner.reach.values():
        for rides in m.values():
            assert not any(rd.reverse for rd in rides if rd.service in loops)


def test_suburban_legs_have_no_stops(analakely_itaosy):
    for it in analakely_itaosy["itineraries"]:
        for leg in it["legs"]:
            if leg["zone"] == "suburbaine":
                assert leg["stops"] == []


def test_unserved_fokontany_gets_walk_access(service, code):
    info = service.resolver.resolve(code("Ivandry", "5e Arrondissement"))
    assert info["served"]["n_direct"] == 0
    assert info["fallback"] and info["warnings"]
    modes = {a["mode"] for a in info["access"].values()}
    assert modes <= {"passage", "proche_a_pied", "repli_a_pied"} and modes & {"proche_a_pied", "repli_a_pied"}
    assert all(a["walk_km"] > 0 for a in info["access"].values() if a["mode"] != "passage")


def test_no_back_and_forth_when_clean_alternative(service, code):
    pairs = [(code("Faliarivo Ambanidia", "2e Arrondissement"), code("Anjanakomboro", "6e Arrondissement")),
             (code("Ivandry", "5e Arrondissement"), code("Ambohimangakely", "Ambohimangakely")),
             (code("Antanimalalaka Analakely", "1er Arrondissement"), code("Itaosy", "Itaosy"))]
    for a, b in pairs:
        r = service.plan(a, b)
        its = r["itineraries"]
        assert its
        assert all(i["revisits"] == 0 for i in its)
        assert len({tuple(i["line_ids"]) for i in its}) == len(its)          # pas de doublon de suite de lignes
        assert r["highlights"]["plus_court"] in {i["id"] for i in its}
        shortest = min(i["total_km"] for i in its)
        assert next(i for i in its if i["id"] == r["highlights"]["plus_court"])["total_km"] == shortest


def test_distance_in_score(analakely_itaosy):
    for it in analakely_itaosy["itineraries"]:
        assert it["score_breakdown"]["distance_en_bus"] == pytest.approx(-1.2 * it["bus_km"], abs=0.05)


def test_far_fokontany_flags_service_limit(service):
    far = next(c for c, f in service.repo.fokontany.items() if f["adm1_pcode"] == "MG71")
    info = service.resolver.resolve(far)
    assert not info["fallback"][0]["within_limit"]
    assert any("Limite de desserte" in w for w in info["warnings"])


def test_same_origin_destination(service, code):
    c = code("Itaosy", "Itaosy")
    r = service.plan(c, c)
    assert r["itineraries"] == [] and r["messages"]


def test_unknown_pcode(service):
    with pytest.raises(NotFoundError):
        service.plan("MG11999999999", "MG11117110001")


def test_search(service):
    assert service.search("Itaosy")[0]["adm4_name"] == "Itaosy"
    assert service.search("MG11118001001")[0]["adm4_pcode"] == "MG11118001001"


def test_always_an_itinerary(service):
    """Garantie : quel que soit le couple de fokontany (hors identiques), au moins un itinéraire est proposé."""
    import random
    rng = random.Random(7)
    pool = sorted(c for c, f in service.repo.fokontany.items() if f["adm1_pcode"] == "MG11")
    far = sorted(c for c, f in service.repo.fokontany.items() if f["adm1_pcode"] == "MG71")[:3]
    pairs = [tuple(rng.sample(pool, 2)) for _ in range(40)] + [(far[0], pool[0]), (pool[5], far[1])]
    for a, b in pairs:
        for k in (0, 2):
            r = service.plan(a, b, k)
            assert r["itineraries"], (a, b, k, r["messages"])
            assert r["search_mode"] in {"normal", "acces_elargi", "approche"}


def test_approach_prefers_buses_over_long_walk(service):
    """Régression : Ambatomahamanina -> Ambatolaona Ouest ne doit pas proposer 38 km de marche en premier."""
    r = service.plan("MG11102379021", "MG11106012001", 2)
    assert r["search_mode"] == "approche"
    best = r["itineraries"][0]
    assert best["walk_km"] < 25 and best["legs"][-1]["line_code"] == "Ligne E"
