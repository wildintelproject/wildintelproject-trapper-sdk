"""
Helper to split a CSV file into several smaller, self-contained CSV files.

Used by the session-based (non-REST) import methods — e.g.
:meth:`~trapper_client.components.locations.LocationsComponent.import_locations`
and :meth:`~trapper_client.components.deployments.DeploymentsComponent.import_deployments`
— to work around servers that reject or time out on very large single-file
uploads. There is no chunked/resumable upload protocol on those endpoints
(unlike :class:`~trapper_client.components.http_uploader.HTTPUploader`), so
"splitting" happens at the CSV row level: each output chunk repeats the
original header row and is a valid, independently-importable CSV on its own.
"""
from __future__ import annotations

import csv
import io
import tempfile
from pathlib import Path

DEFAULT_MAX_CHUNK_BYTES = 512 * 1024


def _row_bytes(row: list[str]) -> int:
    """Return the encoded byte size of one CSV row, including its line terminator."""
    buf = io.StringIO()
    csv.writer(buf).writerow(row)
    return len(buf.getvalue().encode("utf-8"))


def _write_chunk(header: list[str], rows: list[list[str]]) -> Path:
    """Write one header + rows chunk to a new temporary CSV file."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
    )
    writer = csv.writer(tmp)
    writer.writerow(header)
    writer.writerows(rows)
    tmp.close()
    return Path(tmp.name)


def split_csv_by_size(
    file: str | Path, max_bytes: int = DEFAULT_MAX_CHUNK_BYTES
) -> list[Path]:
    """Split a CSV file into several smaller CSV files, each at most ``max_bytes``.

    Each output file repeats the source file's header row, so it is a
    self-contained, independently valid CSV — the row size accounting
    includes that repeated header.

    Args:
        file: Path to the source CSV file.
        max_bytes: Maximum size in bytes of each output chunk (header + rows).
            A single row larger than this on its own is still emitted as a
            (oversized) one-row chunk rather than being dropped or split
            mid-row.

    Returns:
        Paths to the generated temporary chunk files, in row order. Always
        at least one path, even for a header-only or empty source file. The
        caller is responsible for deleting these temp files once done.
    """
    path = Path(file)
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        return [_write_chunk([], [])]

    header, data_rows = rows[0], rows[1:]
    header_bytes = _row_bytes(header)

    chunks: list[Path] = []
    buffer: list[list[str]] = []
    buffer_bytes = header_bytes

    for row in data_rows:
        row_bytes = _row_bytes(row)
        if buffer and buffer_bytes + row_bytes > max_bytes:
            chunks.append(_write_chunk(header, buffer))
            buffer = []
            buffer_bytes = header_bytes
        buffer.append(row)
        buffer_bytes += row_bytes

    if buffer or not chunks:
        chunks.append(_write_chunk(header, buffer))

    return chunks
