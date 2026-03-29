import pytest
import sys
from unittest import mock

try:
    from server.ann import utils
except ImportError:
    pytest.skip('server.ann.utils not importable', allow_module_level=True)

import math

@pytest.fixture(autouse=True)
def patch_vector_dimension(monkeypatch):
    monkeypatch.setattr(utils, 'VECTOR_DIMENSION', 3)


def test_cosine_similarity_basic():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert utils.cosine_similarity(v1, v2) == pytest.approx(1.0)
    v3 = [0.0, 1.0, 0.0]
    assert utils.cosine_similarity(v1, v3) == pytest.approx(0.0)

def test_cosine_similarity_zero_vector():
    v1 = [0.0, 0.0, 0.0]
    v2 = [1.0, 2.0, 3.0]
    assert utils.cosine_similarity(v1, v2) == 0.0

def test_cosine_similarity_dim_mismatch():
    with pytest.raises(ValueError):
        utils.cosine_similarity([1,2], [1,2,3])

def test_cosine_distance():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert utils.cosine_distance(v1, v2) == pytest.approx(0.0)
    v3 = [0.0, 1.0, 0.0]
    assert utils.cosine_distance(v1, v3) == pytest.approx(1.0)

def test_euclidean_distance():
    v1 = [1.0, 2.0, 3.0]
    v2 = [4.0, 6.0, 3.0]
    assert utils.euclidean_distance(v1, v2) == pytest.approx(5.0)

def test_euclidean_distance_dim_mismatch():
    with pytest.raises(ValueError):
        utils.euclidean_distance([1,2], [1,2,3])

def test_normalize_vector():
    v = [3.0, 0.0, 4.0]
    normed = utils.normalize_vector(v)
    norm = math.sqrt(3.0**2 + 4.0**2)
    assert normed == pytest.approx([3.0/norm, 0.0, 4.0/norm])

def test_normalize_vector_zero():
    v = [0.0, 0.0, 0.0]
    assert utils.normalize_vector(v) == v

def test_validate_embedding_valid():
    emb = [0.1, 0.2, 0.3]
    valid, err = utils.validate_embedding(emb)
    assert valid is True
    assert err is None or err == ''

def test_validate_embedding_none():
    valid, err = utils.validate_embedding(None)
    assert not valid
    assert 'None' in err

def test_validate_embedding_type():
    valid, err = utils.validate_embedding('notalist')
    assert not valid
    assert 'list' in err

def test_validate_embedding_dim(monkeypatch):
    monkeypatch.setattr(utils, 'VECTOR_DIMENSION', 4)
    valid, err = utils.validate_embedding([1,2,3])
    assert not valid
    assert 'dimension' in err

def test_validate_embedding_nan_inf():
    emb = [1.0, float('nan'), 3.0]
    valid, err = utils.validate_embedding(emb)
    assert not valid
    emb2 = [1.0, float('inf'), 3.0]
    valid2, err2 = utils.validate_embedding(emb2)
    assert not valid2

def test_validate_embeddings_batch():
    embs = [[0.1,0.2,0.3], None, [1,2,3], [1,2]]
    # Patch VECTOR_DIMENSION to 3
    result = utils.validate_embeddings_batch(embs)
    assert result['total'] == 4
    assert result['null'] == 1
    assert result['invalid'] >= 1
    assert isinstance(result['errors'], list)

def test_format_vector_for_postgres():
    emb = [1.1, 2.2, 3.3]
    s = utils.format_vector_for_postgres(emb)
    assert s.startswith('[') and s.endswith(']')
    assert ',' in s

def test_get_nearest_neighbors_sql():
    sql = utils.get_nearest_neighbors_sql('mytable', 'emb', 5, 'patient_id=123')
    assert 'SELECT' in sql and 'FROM mytable' in sql
    assert 'WHERE patient_id=123 AND' in sql or 'WHERE' in sql

def test_get_patient_events_with_embeddings_sql():
    sql = utils.get_patient_events_with_embeddings_sql('pat123', 'mytable', 10)
    assert 'SELECT' in sql and 'FROM mytable' in sql
    assert 'LIMIT 10' in sql

def test_format_ann_result_tuple():
    row = (1, 'pat', '2020-01-01', 'event', 'src', '{}', 'txt', [0.1,0.2,0.3], 0.5)
    result = utils.format_ann_result(row, include_embedding=True)
    assert 'id' in result and 'embedding' in result

def test_format_ann_result_dict():
    row = {'id': 1, 'patient_id': 'pat', 'embedding': [0.1,0.2,0.3]}
    result = utils.format_ann_result(row, include_embedding=True)
    assert result['id'] == 1
    assert 'embedding' in result

def test_rank_results_by_relevance_distance():
    results = [{'distance': 0.2}, {'distance': 0.1}, {'distance': 0.3}]
    ranked = utils.rank_results_by_relevance(results)
    assert ranked[0]['distance'] == 0.1

def test_rank_results_by_relevance_similarity():
    results = [{'similarity': 0.2}, {'similarity': 0.9}, {'similarity': 0.5}]
    ranked = utils.rank_results_by_relevance(results)
    assert ranked[0]['similarity'] == 0.9

def test_chunk_list():
    lst = list(range(10))
    chunks = utils.chunk_list(lst, 3)
    assert all(isinstance(c, list) for c in chunks)
    assert sum(len(c) for c in chunks) == 10

def test_deduplicate_by_text():
    events = [
        {'text': 'a', 'id': 1},
        {'text': 'b', 'id': 2},
        {'text': 'a', 'id': 3},
        {'text': 'c', 'id': 4},
    ]
    deduped = utils.deduplicate_by_text(events)
    texts = [e['text'] for e in deduped]
    assert len(deduped) == 3
    assert set(texts) == {'a', 'b', 'c'}
