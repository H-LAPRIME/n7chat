import pytest

from backend.db.vector import _format_vector
from backend.flows.index_flow import chunk_text


def test_chunk_text_uses_overlap():
    chunks = chunk_text(" ".join(str(i) for i in range(10)), size=4, overlap=1)

    assert chunks == ["0 1 2 3", "3 4 5 6", "6 7 8 9", "9"]


def test_chunk_text_empty_content():
    assert chunk_text("") == []


def test_format_vector_requires_1024_dimensions():
    with pytest.raises(ValueError):
        _format_vector([0.0, 1.0])


def test_format_vector_outputs_pgvector_literal():
    vector = _format_vector([0.0] * 1024)

    assert vector.startswith("[")
    assert vector.endswith("]")
    assert vector.count(",") == 1023
