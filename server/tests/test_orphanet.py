from fastapi.testclient import TestClient
from server.api.app_postgres import app

client = TestClient(app)

def test_orphanet_search_als():
    """Test search for ALS returns ORPHA:803"""
    r = client.get("/api/orphanet/search?q=ALS&limit=5")
    assert r.status_code == 200
    data = r.json()
    assert len(data) > 0
    orpha_codes = [item["orpha_code"] for item in data]
    assert "ORPHA:803" in orpha_codes

def test_orphanet_search_amyotrophic():
    """Test search for full ALS name"""
    r = client.get("/api/orphanet/search?q=amyotrophic%20lateral%20sclerosis&limit=5")
    assert r.status_code == 200
    data = r.json()
    assert len(data) > 0
    assert data[0]["orpha_code"] == "ORPHA:803"
    assert "amyotrophic lateral sclerosis" in data[0]["name"].lower()

def test_orphanet_disease_detail():
    """Test disease detail endpoint returns comprehensive data"""
    r = client.get("/api/orphanet/disease/ORPHA:803")
    assert r.status_code == 200
    data = r.json()
    
    assert data["orpha_code"] == "ORPHA:803"
    assert data["orpha_num"] == 803
    assert data["name"]
    assert data["disorder_type"]
    
    assert "synonyms" in data
    assert "external_refs" in data
    assert "genes" in data
    assert "phenotypes" in data
    
    if data["synonyms"]:
        assert "term" in data["synonyms"][0]
    if data["external_refs"]:
        assert "source" in data["external_refs"][0]
        assert "ref" in data["external_refs"][0]
    if data["genes"]:
        assert "gene_symbol" in data["genes"][0]
    if data["phenotypes"]:
        assert "hpo_id" in data["phenotypes"][0]

def test_orphanet_disease_numeric_code():
    """Test disease detail with numeric code (should convert to ORPHA: format)"""
    r = client.get("/api/orphanet/disease/803")
    assert r.status_code == 200
    data = r.json()
    assert data["orpha_code"] == "ORPHA:803"

def test_orphanet_disease_not_found():
    """Test 404 for non-existent disease"""
    r = client.get("/api/orphanet/disease/ORPHA:999999")
    assert r.status_code == 404

def test_orphanet_search_validation():
    """Test search query validation"""
    r = client.get("/api/orphanet/search?q=a")
    assert r.status_code == 422
    
    r = client.get("/api/orphanet/search?q=test")
    assert r.status_code == 200

def test_orphanet_stats():
    """Test statistics endpoint"""
    r = client.get("/api/orphanet/stats")
    assert r.status_code == 200
    data = r.json()
    
    expected_fields = ["diseases", "synonyms", "external_refs", "gene_links", "phenotype_links"]
    for field in expected_fields:
        assert field in data
        assert isinstance(data[field], int)
        assert data[field] >= 0
