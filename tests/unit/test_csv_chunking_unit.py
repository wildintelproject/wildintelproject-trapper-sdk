"""
Unit tests for trapper_client.csv_chunking.
"""
from __future__ import annotations

import csv

import pytest

from trapper_client.csv_chunking import split_csv_by_size


def _read_csv(path):
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


@pytest.fixture
def csv_file(tmp_path):
    path = tmp_path / "data.csv"
    rows = ["a,b"] + [f"{i},{i * 2}" for i in range(200)]
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return path


def test_returns_single_chunk_when_under_limit(csv_file):
    """split_csv_by_size() devuelve un único chunk si el fichero ya cabe en max_bytes."""
    chunks = split_csv_by_size(csv_file, max_bytes=1024 * 1024)

    assert len(chunks) == 1
    assert _read_csv(chunks[0]) == _read_csv(csv_file)


def test_splits_into_multiple_chunks_when_over_limit(csv_file):
    """split_csv_by_size() trocea en varios ficheros si excede max_bytes."""
    chunks = split_csv_by_size(csv_file, max_bytes=200)

    assert len(chunks) > 1


def test_every_chunk_repeats_the_header(csv_file):
    """split_csv_by_size() repite la cabecera en cada chunk generado."""
    chunks = split_csv_by_size(csv_file, max_bytes=200)

    for chunk in chunks:
        rows = _read_csv(chunk)
        assert rows[0] == ["a", "b"]


def test_chunks_reconstruct_original_rows_in_order(csv_file):
    """split_csv_by_size() no pierde ni reordena filas al trocear."""
    chunks = split_csv_by_size(csv_file, max_bytes=200)

    original_rows = _read_csv(csv_file)[1:]
    reconstructed = []
    for chunk in chunks:
        reconstructed.extend(_read_csv(chunk)[1:])

    assert reconstructed == original_rows


def test_no_chunk_exceeds_max_bytes_by_much(csv_file):
    """split_csv_by_size() respeta max_bytes salvo por el margen de una fila."""
    max_bytes = 300
    chunks = split_csv_by_size(csv_file, max_bytes=max_bytes)

    for chunk in chunks[:-1]:
        size = chunk.stat().st_size
        assert size <= max_bytes + 50  # margen: tamaño de una fila + header repetido

def test_handles_header_only_file(tmp_path):
    """split_csv_by_size() no revienta con un CSV que solo tiene cabecera."""
    path = tmp_path / "empty.csv"
    path.write_text("a,b\n", encoding="utf-8")

    chunks = split_csv_by_size(path, max_bytes=1024)

    assert len(chunks) == 1
    assert _read_csv(chunks[0]) == [["a", "b"]]


def test_single_oversized_row_becomes_its_own_chunk(tmp_path):
    """Una fila más grande que max_bytes por sí sola no se descarta ni se corta a mitad."""
    path = tmp_path / "big_row.csv"
    long_value = "x" * 1000
    path.write_text(f"a,b\n1,{long_value}\n2,short\n", encoding="utf-8")

    chunks = split_csv_by_size(path, max_bytes=100)

    all_rows = []
    for chunk in chunks:
        all_rows.extend(_read_csv(chunk)[1:])
    assert all_rows == [["1", long_value], ["2", "short"]]


def test_caller_is_responsible_for_cleanup(csv_file):
    """split_csv_by_size() no borra los ficheros temporales que crea."""
    chunks = split_csv_by_size(csv_file, max_bytes=200)

    assert all(chunk.exists() for chunk in chunks)

    for chunk in chunks:
        chunk.unlink()
