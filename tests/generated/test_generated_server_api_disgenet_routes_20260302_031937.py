# Auto-generated tests for server.api.disgenet_routes
import pytest
from unittest import mock

try:
    from server.api import disgenet_routes as mod
except ImportError:
    mod = None

def test_disgenet_stats(monkeypatch):
    if mod is None:
        pytest.skip('server.api.disgenet_routes not importable')
    dummy_rows = [{'rows': 1, 'assoc_ids': 2, 'genes': 3, 'diseases': 4}]
    monkeypatch.setattr(mod, 'pg_read', lambda sql: dummy_rows)
    monkeypatch.setattr(mod, 'JSONResponse', lambda x: x)
    monkeypatch.setattr(mod, 'jsonable_encoder', lambda x: x)
    result = mod.disgenet_stats()
    assert isinstance(result, list)
    assert result[0]['rows'] == 1

def test_disgenet_by_gene(monkeypatch):
    if mod is None:
        pytest.skip('server.api.disgenet_routes not importable')
    dummy_rows = [{'assoc_id': 1, 'gene_symbol': 'TP53', 'disease_name': 'Cancer'}]
    monkeypatch.setattr(mod, 'pg_read', lambda sql, params: dummy_rows)
    monkeypatch.setattr(mod, 'JSONResponse', lambda x: x)
    monkeypatch.setattr(mod, 'jsonable_encoder', lambda x: x)
    result = mod.disgenet_by_gene(symbol='TP53', limit=5)
    assert isinstance(result, list)
    assert result[0]['gene_symbol'] == 'TP53'

def test_disgenet_search(monkeypatch):
    if mod is None:
        pytest.skip('server.api.disgenet_routes not importable')
    dummy_rows = [{'assoc_id': 1, 'gene_symbol': 'TP53', 'disease_name': 'Cancer', 'score': 0.9}]
    monkeypatch.setattr(mod, 'pg_read', lambda sql, params: dummy_rows)
    monkeypatch.setattr(mod, 'JSONResponse', lambda x: x)
    monkeypatch.setattr(mod, 'jsonable_encoder', lambda x: x)
    result = mod.disgenet_search(gene='TP53', disease=None, min_score=0.5, limit=10)
    assert isinstance(result, list)
    assert result[0]['score'] >= 0.5

def test_disgenet_by_disease(monkeypatch):
    if mod is None:
        pytest.skip('server.api.disgenet_routes not importable')
    dummy_rows = [{'assoc_id': 1, 'disease_name': 'Cancer', 'gene_symbol': 'TP53'}]
    monkeypatch.setattr(mod, 'pg_read', lambda sql, params: dummy_rows)
    monkeypatch.setattr(mod, 'JSONResponse', lambda x: x)
    monkeypatch.setattr(mod, 'jsonable_encoder', lambda x: x)
    result = mod.disgenet_by_disease(name='Cancer', limit=5)
    assert isinstance(result, list)
    assert result[0]['disease_name'] == 'Cancer'

def test_disgenet_by_geneid(monkeypatch):
    if mod is None:
        pytest.skip('server.api.disgenet_routes not importable')
    dummy_rows = [{'assoc_id': 1, 'gene_ncbi_id': 1234, 'gene_symbol': 'TP53'}]
    monkeypatch.setattr(mod, 'pg_read', lambda sql, params: dummy_rows)
    monkeypatch.setattr(mod, 'JSONResponse', lambda x: x)
    monkeypatch.setattr(mod, 'jsonable_encoder', lambda x: x)
    result = mod.disgenet_by_geneid(ncbi_id=1234, limit=5)
    assert isinstance(result, list)
    assert result[0]['gene_ncbi_id'] == 1234
