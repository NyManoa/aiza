API = "/api/v1"


def test_health(client):
    assert client.get(f"{API}/health").json() == {"status": "ok"}


def test_cascade(client):
    regions = client.get(f"{API}/regions").json()
    assert regions[0]["pcode"] == "MG11" and len(regions) == 24
    districts = client.get(f"{API}/regions/MG11/districts").json()
    assert len(districts) == 13
    communes = client.get(f"{API}/districts/MG11118/communes").json()
    fk = client.get(f"{API}/communes/{communes[0]['pcode']}/fokontany").json()
    assert len(fk) == 44 and "served" in fk[0]


def test_itineraries_contract(client):
    r = client.get(f"{API}/itineraries", params={"from": "MG11118001001", "to": "MG11117110001"})
    assert r.status_code == 200
    body = r.json()
    leg = body["itineraries"][0]["legs"][0]
    assert {"from", "to", "stops", "direction"} <= set(leg)
    assert body["origin"]["lines_here"][0].keys() >= {"from", "to"}


def test_validation_and_not_found(client):
    assert client.get(f"{API}/itineraries", params={"from": "bad", "to": "MG11117110001"}).status_code == 422
    assert client.get(f"{API}/fokontany/MG11999999999").status_code == 404
    assert client.get(f"{API}/regions/MG99/districts").status_code == 404


def test_openapi_and_gzip(client):
    assert client.get(f"{API}/openapi.json").json()["info"]["title"]
    r = client.get(f"{API}/stats", headers={"Accept-Encoding": "gzip"})
    assert r.headers.get("content-encoding") == "gzip"


def test_works_without_lifespan(settings):
    """Hébergement serverless (Vercel) : le lifespan peut ne pas être exécuté -> création paresseuse du service."""
    from fastapi.testclient import TestClient

    from planner.api.app import create_app
    client = TestClient(create_app(settings))       # sans « with » : le lifespan n'est pas lancé
    assert client.get(f"{API}/regions/MG11/districts").status_code == 200
