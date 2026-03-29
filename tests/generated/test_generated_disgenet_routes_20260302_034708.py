try:
    import pytest
    from server.api import disgenet_routes
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
from unittest.mock import patch, MagicMock

# disgenet_stats

def test_disgenet_stats_returns_json(monkeypatch):
    fake_rows = [{"rows": 1, "assoc_ids": 2, "genes": 3, "diseases": 4}]
    monkeypatch.setattr(disgenet_routes, "pg_read", lambda sql: fake_rows)
    monkeypatch.setattr(disgenet_routes, "JSONResponse", lambda x: x)
    monkeypatch.setattr(disgenet_routes, "jsonable_encoder", lambda x: x)
    result = disgenet_routes.disgenet_stats()
    assert result == fake_rows

# disgenet_by_gene

def test_disgenet_by_gene_basic(monkeypatch):
    fake_rows = [{"assoc_id": 1, "gene_symbol": "TP53"}]
    monkeypatch.setattr(disgenet_routes, "pg_read", lambda sql, params: fake_rows)
    monkeypatch.setattr(disgenet_routes, "JSONResponse", lambda x: x)
    monkeypatch.setattr(disgenet_routes, "jsonable_encoder", lambda x: x)
    result = disgenet_routes.disgenet_by_gene("TP53", 5)
    assert result == fake_rows

# disgenet_search

def test_disgenet_search_basic(monkeypatch):
    fake_rows = [{"assoc_id": 1, "gene_symbol": "TP53", "score": 0.9}]
    monkeypatch.setattr(disgenet_routes, "pg_read", lambda sql, params: fake_rows)
    monkeypatch.setattr(disgenet_routes, "JSONResponse", lambda x: x)
    monkeypatch.setattr(disgenet_routes, "jsonable_encoder", lambda x: x)
    # Patch Query to just return the default value
    monkeypatch.setattr(disgenet_routes, "Query", lambda *a, **k: a[0] if a else None)
    result = disgenet_routes.disgenet_search(gene="TP53", disease=None, min_score=0.5, limit=10)
    assert isinstance(result, list)
    assert result == fake_rows

# disgenet_by_disease

def test_disgenet_by_disease(monkeypatch):
    fake_rows = [{"assoc_id": 2, "disease_name": "Cancer"}]
    monkeypatch.setattr(disgenet_routes, "pg_read", lambda sql, params: fake_rows)
    monkeypatch.setattr(disgenet_routes, "JSONResponse", lambda x: x)
    monkeypatch.setattr(disgenet_routes, "jsonable_encoder", lambda x: x)
    result = disgenet_routes.disgenet_by_disease("Cancer", 3)
    assert result == fake_rows

# disgenet_by_geneid

def test_disgenet_by_geneid(monkeypatch):
    fake_rows = [{"assoc_id": 3, "gene_ncbi_id": 7157}]
    monkeypatch.setattr(disgenet_routes, "pg_read", lambda sql, params: fake_rows)
    monkeypatch.setattr(disgenet_routes, "JSONResponse", lambda x: x)
    monkeypatch.setattr(disgenet_routes, "jsonable_encoder", lambda x: x)
    result = disgenet_routes.disgenet_by_geneid(7157, 2)
    assert result == fake_rows
