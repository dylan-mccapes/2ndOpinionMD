try:
    import pytest
    from server.ann import utils
    import math
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

def test_cosine_similarity_basic():
    v1 = [1.0, 0.0]
    v2 = [0.0, 1.0]
    sim = utils.cosine_similarity(v1, v2)
    assert math.isclose(sim, 0.0)
    sim2 = utils.cosine_similarity([1, 1], [1, 1])
    assert math.isclose(sim2, 1.0)

def test_cosine_similarity_dimension_mismatch():
    with pytest.raises(ValueError):
        utils.cosine_similarity([1, 2], [1])

def test_cosine_distance():
    v1 = [1, 0]
    v2 = [0, 1]
    dist = utils.cosine_distance(v1, v2)
    assert math.isclose(dist, 1.0)
    dist2 = utils.cosine_distance([1, 1], [1, 1])
    assert math.isclose(dist2, 0.0)

def test_euclidean_distance():
    v1 = [0, 0]
    v2 = [3, 4]
    dist = utils.euclidean_distance(v1, v2)
    assert math.isclose(dist, 5.0)

def test_euclidean_distance_dimension_mismatch():
    with pytest.raises(ValueError):
        utils.euclidean_distance([1, 2], [1])

def test_normalize_vector():
    v = [3, 4]
    normed = utils.normalize_vector(v)
    assert math.isclose(math.sqrt(sum(x**2 for x in normed)), 1.0)
    v0 = [0, 0]
    assert utils.normalize_vector(v0) == v0

def test_validate_embedding(monkeypatch):
    monkeypatch.setattr(utils, 'VECTOR_DIMENSION', 3)
    valid = [0.1, 0.2, 0.3]
    is_valid, err = utils.validate_embedding(valid)
    assert is_valid
    assert err is None or err == ''
    is_valid, err = utils.validate_embedding(None)
    assert not is_valid and 'None' in err
    is_valid, err = utils.validate_embedding([1, 2])
    assert not is_valid and 'dimension' in err
    is_valid, err = utils.validate_embedding([1, float('nan'), 3])
    assert not is_valid
    is_valid, err = utils.validate_embedding([1, 'a', 3])
    assert not is_valid

def test_validate_embeddings_batch(monkeypatch):
    monkeypatch.setattr(utils, 'VECTOR_DIMENSION', 2)
    batch = [[1.0, 2.0], None, [1.0, 2.0], [1.0, 2.0, 3.0]]
    result = utils.validate_embeddings_batch(batch)
    assert result['total'] == 4
    assert result['null'] == 1
    assert result['valid'] == 2
    assert result['invalid'] == 1
    assert isinstance(result['errors'], list)

def test_format_vector_for_postgres():
    v = [1.1, 2.2, 3.3]
    s = utils.format_vector_for_postgres(v)
    assert s.startswith('[') and s.endswith(']')
    assert ',' in s

def test_get_nearest_neighbors_sql():
    sql = utils.get_nearest_neighbors_sql('tbl', 'emb', 5, 'patient_id=1')
    assert 'tbl' in sql and 'emb' in sql and 'LIMIT 5' in sql
    assert 'WHERE patient_id=1 AND' in sql or 'WHERE' in sql

def test_get_patient_events_with_embeddings_sql():
    sql = utils.get_patient_events_with_embeddings_sql('pat123', 'tbl', 10)
    assert 'pat123' in sql and 'tbl' in sql and 'LIMIT 10' in sql

def test_format_ann_result_tuple():
    row = (1, 'pat', '2020-01-01', 'event', 'src', '{}', 'txt', [0.1, 0.2], 0.5)
    res = utils.format_ann_result(row, include_embedding=True)
    assert res['id'] == 1
    assert 'embedding' in res

def test_format_ann_result_dict():
    row = {'id': 2, 'patient_id': 'p', 'embedding': [0.1, 0.2]}
    res = utils.format_ann_result(row)
    assert res['id'] == 2

def test_rank_results_by_relevance_distance():
    results = [{'distance': 0.2}, {'distance': 0.1}, {'distance': 0.3}]
    ranked = utils.rank_results_by_relevance(results)
    assert ranked[0]['distance'] == 0.1

def test_rank_results_by_relevance_similarity():
    results = [{'similarity': 0.5}, {'similarity': 0.9}, {'similarity': 0.1}]
    ranked = utils.rank_results_by_relevance(results)
    assert ranked[0]['similarity'] == 0.9

def test_chunk_list():
    lst = list(range(10))
    chunks = utils.chunk_list(lst, 3)
    assert all(isinstance(chunk, list) for chunk in chunks)
    assert sum(len(chunk) for chunk in chunks) == 10
    assert len(chunks) == 4

def test_deduplicate_by_text():
    events = [
        {'text': 'a', 'id': 1},
        {'text': 'b', 'id': 2},
        {'text': 'a', 'id': 3},
        {'text': 'c', 'id': 4}
    ]
    deduped = utils.deduplicate_by_text(events)
    texts = [e['text'] for e in deduped]
    assert set(texts) == {'a', 'b', 'c'}
    assert len(deduped) == 3
