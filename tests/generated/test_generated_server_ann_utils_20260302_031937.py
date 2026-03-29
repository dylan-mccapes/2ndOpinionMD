import pytest
from unittest import mock

try:
    from server.ann import utils
except ImportError:
    pytest.skip('server.ann.utils not importable', allow_module_level=True)

import math

# cosine_similarity

def test_cosine_similarity_identical():
    v = [1.0, 2.0, 3.0]
    assert math.isclose(utils.cosine_similarity(v, v), 1.0)

def test_cosine_similarity_orthogonal():
    v1 = [1, 0]
    v2 = [0, 1]
    assert math.isclose(utils.cosine_similarity(v1, v2), 0.0)

def test_cosine_similarity_zero_vector():
    v1 = [0, 0, 0]
    v2 = [1, 2, 3]
    assert utils.cosine_similarity(v1, v2) == 0.0

def test_cosine_similarity_dimension_mismatch():
    with pytest.raises(ValueError):
        utils.cosine_similarity([1, 2], [1, 2, 3])

# cosine_distance

def test_cosine_distance():
    v1 = [1, 0]
    v2 = [0, 1]
    assert math.isclose(utils.cosine_distance(v1, v2), 1.0)
    v3 = [1, 0]
    assert math.isclose(utils.cosine_distance(v1, v3), 0.0)

# euclidean_distance

def test_euclidean_distance():
    v1 = [0, 0]
    v2 = [3, 4]
    assert math.isclose(utils.euclidean_distance(v1, v2), 5.0)

def test_euclidean_distance_dimension_mismatch():
    with pytest.raises(ValueError):
        utils.euclidean_distance([1, 2], [1, 2, 3])

# normalize_vector

def test_normalize_vector():
    v = [3, 4]
    normed = utils.normalize_vector(v)
    assert math.isclose(math.sqrt(sum(x*x for x in normed)), 1.0)

def test_normalize_vector_zero():
    v = [0, 0, 0]
    assert utils.normalize_vector(v) == v

# validate_embedding

def test_validate_embedding_valid(monkeypatch):
    monkeypatch.setattr(utils, 'VECTOR_DIMENSION', 3)
    valid, err = utils.validate_embedding([1.0, 2.0, 3.0])
    assert valid is True
    assert err is None

def test_validate_embedding_none():
    valid, err = utils.validate_embedding(None)
    assert not valid
    assert 'None' in err

def test_validate_embedding_type(monkeypatch):
    monkeypatch.setattr(utils, 'VECTOR_DIMENSION', 2)
    valid, err = utils.validate_embedding('notalist')
    assert not valid
    assert 'list' in err

def test_validate_embedding_dimension(monkeypatch):
    monkeypatch.setattr(utils, 'VECTOR_DIMENSION', 2)
    valid, err = utils.validate_embedding([1.0])
    assert not valid
    assert 'dimension' in err

def test_validate_embedding_nan_inf(monkeypatch):
    monkeypatch.setattr(utils, 'VECTOR_DIMENSION', 2)
    valid, err = utils.validate_embedding([1.0, float('nan')])
    assert not valid
    assert 'NaN' in err or 'nan' in err.lower() or 'not finite' in err.lower()
    valid, err = utils.validate_embedding([1.0, float('inf')])
    assert not valid
    assert 'Inf' in err or 'inf' in err.lower() or 'not finite' in err.lower()

def test_validate_embedding_non_numeric(monkeypatch):
    monkeypatch.setattr(utils, 'VECTOR_DIMENSION', 2)
    valid, err = utils.validate_embedding([1.0, 'a'])
    assert not valid
    assert 'not numeric' in err

# validate_embeddings_batch

def test_validate_embeddings_batch(monkeypatch):
    monkeypatch.setattr(utils, 'VECTOR_DIMENSION', 2)
    embs = [[1.0, 2.0], None, [1.0], [1.0, float('nan')]]
    result = utils.validate_embeddings_batch(embs)
    assert result['total'] == 4
    assert result['valid'] == 1
    assert result['null'] == 1
    assert result['invalid'] == 2
    assert len(result['errors']) == 2

# format_vector_for_postgres

def test_format_vector_for_postgres():
    emb = [1.1, 2.2, 3.3]
    s = utils.format_vector_for_postgres(emb)
    assert s == '[1.1,2.2,3.3]'

# get_nearest_neighbors_sql

def test_get_nearest_neighbors_sql_default():
    sql = utils.get_nearest_neighbors_sql()
    assert 'SELECT' in sql and 'embedding' in sql and 'LIMIT' in sql

def test_get_nearest_neighbors_sql_with_where():
    sql = utils.get_nearest_neighbors_sql(table_name='t', embedding_column='e', limit=5, where_clause='patient_id=42')
    assert 'WHERE patient_id=42 AND' in sql or 'WHERE' in sql
    assert 'LIMIT 5' in sql

# get_patient_events_with_embeddings_sql

def test_get_patient_events_with_embeddings_sql():
    sql = utils.get_patient_events_with_embeddings_sql('pat123', table_name='t', limit=10)
    assert 'SELECT' in sql and 'pat123' in sql and 'LIMIT 10' in sql

# format_ann_result

def test_format_ann_result_dict():
    row = {'id': 1, 'patient_id': 'p', 'ts': 't', 'event_type': 'e', 'source': 's', 'structured': {}, 'text': 'txt', 'embedding': [1,2,3], 'distance': 0.1}
    res = utils.format_ann_result(row, include_embedding=True)
    assert res['id'] == 1
    assert 'embedding' in res

def test_format_ann_result_tuple():
    row = (1, 'p', 't', 'e', 's', {}, 'txt', [1,2,3], 0.1)
    res = utils.format_ann_result(row, include_embedding=True)
    assert res['id'] == 1
    assert 'embedding' in res

class DummyRow:
    def __init__(self):
        self._mapping = {'id': 1, 'patient_id': 'p', 'ts': 't', 'event_type': 'e', 'source': 's', 'structured': {}, 'text': 'txt', 'embedding': [1,2,3], 'distance': 0.1}

def test_format_ann_result_sqlalchemy():
    row = DummyRow()
    res = utils.format_ann_result(row, include_embedding=True)
    assert res['id'] == 1
    assert 'embedding' in res

# rank_results_by_relevance

def test_rank_results_by_distance():
    results = [{'distance': 0.2}, {'distance': 0.1}, {'distance': 0.3}]
    ranked = utils.rank_results_by_relevance(results)
    assert ranked[0]['distance'] == 0.1

def test_rank_results_by_similarity():
    results = [{'similarity': 0.2}, {'similarity': 0.9}, {'similarity': 0.5}]
    ranked = utils.rank_results_by_relevance(results)
    assert ranked[0]['similarity'] == 0.9

def test_rank_results_by_default():
    results = [{'foo': 1}, {'foo': 2}]
    ranked = utils.rank_results_by_relevance(results)
    assert ranked == results

# chunk_list

def test_chunk_list():
    lst = list(range(10))
    chunks = utils.chunk_list(lst, 3)
    assert len(chunks) == 4
    assert chunks[0] == [0,1,2]
    assert chunks[-1] == [9]

# deduplicate_by_text

def test_deduplicate_by_text():
    events = [
        {'text': 'a', 'id': 1},
        {'text': 'b', 'id': 2},
        {'text': 'a', 'id': 3},
        {'text': 'c', 'id': 4},
        {'text': 'b', 'id': 5}
    ]
    deduped = utils.deduplicate_by_text(events)
    texts = [e['text'] for e in deduped]
    assert texts == ['a', 'b', 'c']
