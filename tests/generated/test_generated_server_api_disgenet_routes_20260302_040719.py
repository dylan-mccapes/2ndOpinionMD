try:
    from server.api import disgenet_routes
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
import pytest
from unittest.mock import patch

def test_disgenet_stats(monkeypatch):
    fake_rows = [{"rows": 1, "assoc_ids": 2, "genes": 3, "diseases": 4}]
    monkeypatch.setattr(disgenet_routes, "pg_read", lambda sql: fake_rows)
    monkeypatch.setattr(disgenet_routes, "JSONResponse", lambda x: x)
    monkeypatch.setattr(disgenet_routes, "jsonable_encoder", lambda x: x)
    result = disgenet_routes.disgenet_stats()
    assert result == fake_rows

def test_disgenet_by_gene(monkeypatch):
    fake_rows = [{"assoc_id": 1, "gene_symbol": "TP53"}]
    monkeypatch.setattr(disgenet_routes, "pg_read", lambda sql, params: fake_rows)
    monkeypatch.setattr(disgenet_routes, "JSONResponse", lambda x: x)
    monkeypatch.setattr(disgenet_routes, "jsonable_encoder", lambda x: x)
    result = disgenet_routes.disgenet_by_gene(symbol="TP53", limit=5)
    assert result == fake_rows

def test_disgenet_search(monkeypatch):
    fake_rows = [{"assoc_id": 1, "gene_symbol": "TP53", "score": 0.9}]
    monkeypatch.setattr(disgenet_routes, "pg_read", lambda sql, params: fake_rows)
    monkeypatch.setattr(disgenet_routes, "JSONResponse", lambda x: x)
    monkeypatch.setattr(disgenet_routes, "jsonable_encoder", lambda x: x)
    result = disgenet_routes.disgenet_search(gene="TP53", disease=None, min_score=0.5, limit=10)
    assert result == fake_rows

def test_disgenet_by_disease(monkeypatch):
    fake_rows = [{"assoc_id": 1, "disease_name": "Cancer"}]
    monkeypatch.setattr(disgenet_routes, "pg_read", lambda sql, params: fake_rows)
    monkeypatch.setattr(disgenet_routes, "JSONResponse", lambda x: x)
    monkeypatch.setattr(disgenet_routes, "jsonable_encoder", lambda x: x)
    result = disgenet_routes.disgenet_by_disease(name="Cancer", limit=2)
    assert result == fake_rows

def test_disgenet_by_geneid(monkeypatch):
    fake_rows = [{"assoc_id": 1, "gene_ncbi_id": 7157}]
    monkeypatch.setattr(disgenet_routes, "pg_read", lambda sql, params: fake_rows)
    monkeypatch.setattr(disgenet_routes, "JSONResponse", lambda x: x)
    monkeypatch.setattr(disgenet_routes, "jsonable_encoder", lambda x: x)
    result = disgenet_routes.disgenet_by_geneid(ncbi_id=7157, limit=1)
    assert result == fake_rows
