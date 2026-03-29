try:
    import pytest
    from server.ann import utils
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)


def test_cosine_similarity_identical():
    v = [1.0, 0.0, 0.0]
    assert utils.cosine_similarity(v, v) == pytest.approx(1.0)

def test_cosine_similarity_orthogonal():
    v1 = [1.0, 0.0]
    v2 = [0.0, 1.0]
    assert utils.cosine_similarity(v1, v2) == pytest.approx(0.0)

def test_cosine_distance():
    v1 = [1.0, 0.0]
    v2 = [0.0, 1.0]
    assert utils.cosine_distance(v1, v2) == pytest.approx(1.0)

def test_euclidean_distance():
    v1 = [0.0, 0.0]
    v2 = [3.0, 4.0]
    assert utils.euclidean_distance(v1, v2) == pytest.approx(5.0)

def test_normalize_vector():
    v = [3.0, 4.0]
    normed = utils.normalize_vector(v)
    assert pytest.approx(sum(x**2 for x in normed), 1e-6) == 1.0

def test_normalize_vector_zero():
    v = [0.0, 0.0]
    assert utils.normalize_vector(v) == v

def test_validate_embedding_valid(monkeypatch):
    monkeypatch.setattr(utils, 'VECTOR_DIMENSION', 3)
    valid, err = utils.validate_embedding([1.0, 2.0, 3.0])
    assert valid is True
    assert err is None

def test_validate_embedding_none():
    valid, err = utils.validate_embedding(None)
    assert not valid
    assert 'None' in err

def test_validate_embedding_wrong_type(monkeypatch):
    monkeypatch.setattr(utils, 'VECTOR_DIMENSION', 2)
    valid, err = utils.validate_embedding('notalist')
    assert not valid
    assert 'list' in err

def test_validate_embedding_wrong_dim(monkeypatch):
    monkeypatch.setattr(utils, 'VECTOR_DIMENSION', 2)
    valid, err = utils.validate_embedding([1.0])
    assert not valid
    assert 'dimension' in err

def test_validate_embeddings_batch(monkeypatch):
    monkeypatch.setattr(utils, 'VECTOR_DIMENSION', 2)
    batch = [[1.0, 2.0], None, [1.0]]
    result = utils.validate_embeddings_batch(batch)
    assert result['total'] == 3
    assert result['null'] == 1
    assert result['invalid'] == 1
    assert result['valid'] == 1

def test_format_vector_for_postgres():
    v = [1.0, 2.0, 3.0]
    s = utils.format_vector_for_postgres(v)
    assert s == '[1.0,2.0,3.0]'

def test_get_nearest_neighbors_sql():
    sql = utils.get_nearest_neighbors_sql('tbl', 'emb', 5, 'id > 0')
    assert 'SELECT' in sql and 'FROM tbl' in sql and 'WHERE id > 0' in sql

def test_get_patient_events_with_embeddings_sql():
    sql = utils.get_patient_events_with_embeddings_sql('pat123', 'tbl', 10)
    assert 'SELECT' in sql and 'FROM tbl' in sql and 'pat123' in sql

def test_format_ann_result_tuple():
    row = (1, 'pat', '2020-01-01', 'event', 'src', '{}', 'txt', [1.0, 2.0], 0.5)
    result = utils.format_ann_result(row, include_embedding=True)
    assert result['id'] == 1
    assert 'embedding' in result

def test_format_ann_result_dict():
    row = {'id': 2, 'patient_id': 'pat2', 'embedding': [1.0, 2.0]}
    result = utils.format_ann_result(row, include_embedding=True)
    assert result['id'] == 2
    assert 'embedding' in result

def test_rank_results_by_relevance_distance():
    results = [{'distance': 0.2}, {'distance': 0.1}]
    ranked = utils.rank_results_by_relevance(results)
    assert ranked[0]['distance'] <= ranked[1]['distance']

def test_rank_results_by_relevance_similarity():
    results = [{'similarity': 0.5}, {'similarity': 0.9}]
    ranked = utils.rank_results_by_relevance(results)
    assert ranked[0]['similarity'] >= ranked[1]['similarity']

def test_chunk_list():
    lst = list(range(7))
    chunks = utils.chunk_list(lst, 3)
    assert chunks == [[0,1,2],[3,4,5],[6]]

def test_deduplicate_by_text():
    events = [{'text': 'a'}, {'text': 'b'}, {'text': 'a'}]
    deduped = utils.deduplicate_by_text(events)
    assert len(deduped) == 2
    assert {'text': 'a'} in deduped and {'text': 'b'} in deduped
