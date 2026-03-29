import pytest
from unittest import mock

try:
    from server.api import disgenet_routes as dr
except ImportError:
    pytest.skip("server.api.disgenet_routes not importable", allow_module_level=True)

def test_disgenet_stats(monkeypatch):
    monkeypatch.setattr(dr, "pg_read", lambda sql: [{"rows": 1, "assoc_ids": 2, "genes": 3, "diseases": 4}])
    monkeypatch.setattr(dr, "JSONResponse", lambda x: x)
    monkeypatch.setattr(dr, "jsonable_encoder", lambda x: x)
    result = dr.disgenet_stats()
    assert result[0]["rows"] == 1

def test_disgenet_by_gene(monkeypatch):
    monkeypatch.setattr(dr, "pg_read", lambda sql, params: [{"gene_symbol": params[0]}])
    monkeypatch.setattr(dr, "JSONResponse", lambda x: x)
    monkeypatch.setattr(dr, "jsonable_encoder", lambda x: x)
    result = dr.disgenet_by_gene("TP53", 5)
    assert result[0]["gene_symbol"] == "TP53"

def test_disgenet_search(monkeypatch):
    monkeypatch.setattr(dr, "pg_read", lambda sql, params: [{"score": 0.9, "gene_symbol": "G", "disease_name": "D"}])
    monkeypatch.setattr(dr, "JSONResponse", lambda x: x)
    monkeypatch.setattr(dr, "jsonable_encoder", lambda x: x)
    result = dr.disgenet_search(gene="G", disease="D", min_score=0.5, limit=10)
    assert result[0]["score"] == 0.9

def test_disgenet_by_disease(monkeypatch):
    monkeypatch.setattr(dr, "pg_read", lambda sql, params: [{"disease_name": params[0]}])
    monkeypatch.setattr(dr, "JSONResponse", lambda x: x)
    monkeypatch.setattr(dr, "jsonable_encoder", lambda x: x)
    result = dr.disgenet_by_disease("RA", 3)
    assert result[0]["disease_name"] == "RA"

def test_disgenet_by_geneid(monkeypatch):
    monkeypatch.setattr(dr, "pg_read", lambda sql, params: [{"gene_ncbi_id": params[0]}])
    monkeypatch.setattr(dr, "JSONResponse", lambda x: x)
    monkeypatch.setattr(dr, "jsonable_encoder", lambda x: x)
    result = dr.disgenet_by_geneid(1234, 2)
    assert result[0]["gene_ncbi_id"] == 1234
