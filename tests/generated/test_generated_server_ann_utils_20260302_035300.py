import pytest
try:
    from server.ann import utils
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
import math
from unittest.mock import patch, MagicMock


def test_cosine_similarity_identical():
    v = [1.0, 2.0, 3.0]
    assert utils.cosine_similarity(v, v) == pytest.approx(1.0)

def test_cosine_similarity_orthogonal():
    v1 = [1, 0]
    v2 = [0, 1]
    assert utils.cosine_similarity(v1, v2) == pytest.approx(0.0)

def test_cosine_similarity_dimension_mismatch():
    with pytest.raises(ValueError):
        utils.cosine_similarity([1,2], [1,2,3])


def test_cosine_distance_basic():
    v1 = [1, 0]
    v2 = [0, 1]
    dist = utils.cosine_distance(v1, v2)
    assert dist == pytest.approx(1.0)


def test_euclidean_distance_basic():
    v1 = [0, 0]
    v2 = [3, 4]
    assert utils.euclidean_distance(v1, v2) == pytest.approx(5.0)

def test_euclidean_distance_dimension_mismatch():
    with pytest.raises(ValueError):
        utils.euclidean_distance([1], [1,2])


def test_normalize_vector_unit():
    v = [3, 4]
    normed = utils.normalize_vector(v)
    length = math.sqrt(sum(x*x for x in normed))
    assert length == pytest.approx(1.0)

def test_normalize_vector_zero():
    v = [0, 0, 0]
    assert utils.normalize_vector(v) == v


def test_validate_embedding_valid(monkeypatch):
    monkeypatch.setattr(utils, 'VECTOR_DIMENSION', 3)
    emb = [0.1, 0.2, 0.3]
    valid, err = utils.validate_embedding(emb)
    assert valid is True
    assert err is None or err == ''

def test_validate_embedding_none(monkeypatch):
    valid, err = utils.validate_embedding(None)
    assert not valid
    assert "None" in err

def test_validate_embedding_wrong_type(monkeypatch):
    valid, err = utils.validate_embedding("notalist")
    assert not valid
    assert "list" in err

def test_validate_embedding_wrong_dim(monkeypatch):
    monkeypatch.setattr(utils, 'VECTOR_DIMENSION', 2)
    valid, err = utils.validate_embedding([1.0])
    assert not valid
    assert "dimension" in err

def test_validate_embedding_nan_inf(monkeypatch):
    monkeypatch.setattr(utils, 'VECTOR_DIMENSION', 2)
    valid, err = utils.validate_embedding([float('nan'), 1.0])
    assert not valid
    valid2, err2 = utils.validate_embedding([float('inf'), 1.0])
    assert not valid2


def test_validate_embeddings_batch(monkeypatch):
    monkeypatch.setattr(utils, 'VECTOR_DIMENSION', 2)
    batch = [[1.0, 2.0], None, [float('nan'), 1.0], [1.0, 2.0]]
    result = utils.validate_embeddings_batch(batch)
    assert result['total'] == 4
    assert result['null'] == 1
    assert result['invalid'] >= 1
    assert result['valid'] >= 1


def test_format_vector_for_postgres():
    emb = [1.1, 2.2, 3.3]
    s = utils.format_vector_for_postgres(emb)
    assert s.startswith('[') and s.endswith(']')
    assert ',' in s


def test_get_nearest_neighbors_sql_basic():
    sql = utils.get_nearest_neighbors_sql(table_name="mytable", embedding_column="emb", limit=5, where_clause="patient_id='x'")
    assert "SELECT" in sql and "mytable" in sql and ":query_embedding" in sql


def test_get_patient_events_with_embeddings_sql():
    sql = utils.get_patient_events_with_embeddings_sql("patid", table_name="t", limit=10)
    assert "SELECT" in sql and "patid" in sql and "t" in sql


def test_format_ann_result_tuple():
    row = (1, 'pat', '2023-01-01', 'lab', 'src', '{}', 'text', [0.1, 0.2], 0.5)
    result = utils.format_ann_result(row, include_embedding=True)
    assert isinstance(result, dict)
    assert 'id' in result and 'embedding' in result


def test_format_ann_result_dict():
    row = {'id': 1, 'patient_id': 'pat', 'embedding': [0.1, 0.2]}
    result = utils.format_ann_result(row, include_embedding=True)
    assert result['embedding'] == [0.1, 0.2]


def test_rank_results_by_relevance_distance():
    results = [
        {"distance": 0.2},
        {"distance": 0.1},
        {"distance": 0.3}
    ]
    ranked = utils.rank_results_by_relevance(results)
    assert ranked[0]['distance'] <= ranked[1]['distance'] <= ranked[2]['distance']


def test_rank_results_by_relevance_similarity():
    results = [
        {"similarity": 0.2},
        {"similarity": 0.9},
        {"similarity": 0.5}
    ]
    ranked = utils.rank_results_by_relevance(results)
    assert ranked[0]['similarity'] >= ranked[1]['similarity'] >= ranked[2]['similarity']


def test_chunk_list_basic():
    lst = list(range(10))
    chunks = utils.chunk_list(lst, 3)
    assert all(isinstance(c, list) for c in chunks)
    assert sum(len(c) for c in chunks) == 10


def test_deduplicate_by_text():
    events = [
        {"text": "a", "id": 1},
        {"text": "b", "id": 2},
        {"text": "a", "id": 3}
    ]
    deduped = utils.deduplicate_by_text(events)
    texts = [e['text'] for e in deduped]
    assert texts == ['a', 'b']
