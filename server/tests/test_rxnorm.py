from fastapi.testclient import TestClient
from server.api.app_postgres import app

client = TestClient(app)

def test_ndc_has_label():
    r = client.get("/api/rxnorm/ndc/0009-3015-01")
    assert r.status_code == 200
    data = r.json()
    assert data["matches"][0]["str"]  # non-null label

def test_drug_preferred_name():
    r = client.get("/api/rxnorm/drug/993781")
    assert r.status_code == 200
    assert r.json()["concept"]["preferred_name"]

