from planner.core.text import basic_norm, contains_tokens, norm, parse_place_label


def test_basic_norm():
    assert basic_norm("Tsaralalàna") == "tsaralalana"
    assert basic_norm("Fasan'karana") == "fasan karana"
    assert basic_norm("Antananarivo (67 HA)") == "antananarivo 67ha"
    assert basic_norm("  Analamahitsy  cité ") == "analamahitsy cite"


def test_token_alias():
    assert norm("Anosizato antsinananana") == norm("Anosizato Antsinana")


def test_contains_tokens_whole_words():
    assert contains_tokens("antanimalalaka analakely".split(), ["analakely"])
    assert not contains_tokens("mahazoarivo ambohidraserika".split(), ["mahazo"])


def test_parse_label():
    p = parse_place_label("Antananarivo (67 HA)")[0]
    assert (p["name"], p["context"]) == ("67 HA", "Antananarivo")
    p = parse_place_label("Ivato (Passant par Ambohijanahary)")[0]
    assert (p["name"], p["via"]) == ("Ivato", "Ambohijanahary")
    p = parse_place_label("Beravina Passant par Bevalala")[0]
    assert (p["name"], p["via"]) == ("Beravina", "Bevalala")
    assert [a["name"] for a in parse_place_label("Antananandrano / Soavimasoandro")] == ["Antananandrano", "Soavimasoandro"]
    p = parse_place_label("Ambohibao (cycle)")[0]
    assert (p["name"], p["annotation"], p["qualifier"]) == ("Ambohibao", "cycle", None)
