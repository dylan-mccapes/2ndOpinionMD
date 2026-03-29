try:
    import pytest
    from server.ann import utils
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

import math

def test_cosine_similarity_basic():
    v1 = [1, 0]
    v2 = [0, 1]
    assert math.isclose(utils.cosine_similarity(v1, v2), 0.0)
    v3 = [1, 1]
    assert math.isclose(utils.cosine_similarity(v3, v3), 1.0)

def test_cosine_similarity_zero_vector():
    v1 = [0, 0]
    v2 = [1, 1]
    assert utils.cosine_similarity(v1, v2) == 0.0

def test_cosine_similarity_dimension_mismatch():
    with pytest.raises(ValueError):
        utils.cosine_similarity([1, 2], [1])

def test_cosine_distance():
    v1 = [1, 0]
    v2 = [0, 1]
    d = utils.cosine_distance(v1, v2)
    assert math.isclose(d, 1.0)

def test_euclidean_distance():
    v1 = [0, 0]
    v2 = [3, 4]
    assert math.isclose(utils.euclidean_distance(v1, v2), 5.0)

def test_euclidean_distance_dimension_mismatch():
    with pytest.raises(ValueError):
        utils.euclidean_distance([1, 2], [1])

def test_normalize_vector():
    v = [3, 4]
    normed = utils.normalize_vector(v)
    assert math.isclose(math.sqrt(normed[0]**2 + normed[1]**2), 1.0)

def test_normalize_vector_zero():
    v = [0, 0]
    assert utils.normalize_vector(v) == [0, 0]

def test_validate_embedding(monkeypatch):
    monkeypatch.setattr(utils, 'VECTOR_DIMENSION', 2)
    valid, err = utils.validate_embedding([1.0, 2.0])
    assert valid
    valid, err = utils.validate_embedding(None)
    assert not valid and 'None' in err
    valid, err = utils.validate_embedding([1.0])
    assert not valid and 'dimension' in err
    valid, err = utils.validate_embedding(['a', 2.0])
    assert not valid and 'not numeric' in err
    valid, err = utils.validate_embedding([float('nan'), 2.0])
    assert not valid and 'NaN' in err
    valid, err = utils.validate_embedding([float('inf'), 2.0])
    assert not valid and 'infinite' in err

def test_validate_embeddings_batch(monkeypatch):
    monkeypatch.setattr(utils, 'VECTOR_DIMENSION', 2)
    batch = [[1.0, 2.0], None, [1.0], ['a', 2.0]]
    res = utils.validate_embeddings_batch(batch)
    assert res['total'] == 4
    assert res['valid'] == 1
    assert res['null'] == 1
    assert res['invalid'] == 2
    assert len(res['errors']) == 2

def test_format_vector_for_postgres():
    v = [1.1, 2.2, 3.3]
    s = utils.format_vector_for_postgres(v)
    assert s == '[1.1,2.2,3.3]'

def test_get_nearest_neighbors_sql():
    sql = utils.get_nearest_neighbors_sql('mytable', 'emb', 5, 'id > 0')
    assert 'SELECT' in sql and 'mytable' in sql and 'WHERE id > 0 AND' in sql
    sql2 = utils.get_nearest_neighbors_sql()
    assert 'ehr.patient_timeline' in sql2

def test_get_patient_events_with_embeddings_sql():
    sql = utils.get_patient_events_with_embeddings_sql('pat123', 'mytable', 10)
    assert 'pat123' in sql and 'mytable' in sql

def test_format_ann_result_tuple():
    row = (1, 'pat', 'ts', 'etype', 'src', '{}', 'txt', '[1,2,3]', 0.5)
    res = utils.format_ann_result(row)
    assert res['id'] == 1
    assert res['text'] == 'txt'

def test_format_ann_result_dict():
    row = {'id': 1, 'patient_id': 'pat', 'text': 'txt'}
    res = utils.format_ann_result(row)
    assert res['id'] == 1
    assert res['text'] == 'txt'

def test_rank_results_by_relevance_distance():
    results = [{'distance': 0.2}, {'distance': 0.1}, {'distance': 0.3}]
    ranked = utils.rank_results_by_relevance(results)
    assert ranked[0]['distance'] == 0.1

def test_rank_results_by_relevance_similarity():
    results = [{'similarity': 0.2}, {'similarity': 0.9}, {'similarity': 0.3}]
    ranked = utils.rank_results_by_relevance(results)
    assert ranked[0]['similarity'] == 0.9

def test_chunk_list():
    lst = list(range(10))
    chunks = utils.chunk_list(lst, 3)
    assert chunks[0] == [0,1,2]
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
    assert texts == ['a', 'b', 'c']
