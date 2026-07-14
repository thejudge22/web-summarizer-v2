import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
from zipfile import ZIP_DEFLATED, ZipFile


DEFAULT_TITLE_FALLBACK = "📝 Untitled summary"
MAX_BULK_SELECTION = 100
MAX_TITLE_LENGTH = 120


def get_database_path(database_path: Path | None = None) -> Path:
    return database_path or Path(os.getenv("SUMMARY_DATA_DIR", "data")) / "summaries.db"


@contextmanager
def _connect(database_path: Path | None = None):
    path = get_database_path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode = WAL")
    try:
        yield connection
    except Exception:
        connection.rollback()
        raise
    else:
        connection.commit()
    finally:
        connection.close()


def initialize_database(database_path: Path | None = None) -> None:
    with _connect(database_path) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS summaries ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "title TEXT NOT NULL, "
            "source_url TEXT NOT NULL, "
            "source_type TEXT NOT NULL, "
            "markdown TEXT NOT NULL, "
            "created_at TEXT NOT NULL, "
            "updated_at TEXT NOT NULL)"
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record(row: sqlite3.Row, include_markdown: bool = True) -> dict:
    record = dict(row)
    if not include_markdown:
        record.pop("markdown")
        record["source_host"] = urlparse(record["source_url"]).hostname or record["source_url"]
    return record


def create_summary(title, source_url, source_type, markdown, database_path=None):
    timestamp = _now()
    with _connect(database_path) as connection:
        cursor = connection.execute(
            "INSERT INTO summaries (title, source_url, source_type, markdown, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (validate_title(title), source_url, source_type, markdown, timestamp, timestamp),
        )
        row = connection.execute("SELECT * FROM summaries WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _record(row)


def list_summaries(database_path=None):
    with _connect(database_path) as connection:
        rows = connection.execute("SELECT * FROM summaries ORDER BY created_at DESC, id DESC").fetchall()
    return [_record(row, False) for row in rows]


def get_summary(summary_id, database_path=None):
    with _connect(database_path) as connection:
        row = connection.execute("SELECT * FROM summaries WHERE id = ?", (summary_id,)).fetchone()
    return _record(row) if row else None


def validate_title(value):
    if not isinstance(value, str):
        raise ValueError("A title is required")
    title = value.strip()
    if not title or len(title) > MAX_TITLE_LENGTH:
        raise ValueError("A title must contain 1 to 120 characters")
    return title


def validate_summary_ids(value):
    if not isinstance(value, list) or not value or len(value) > MAX_BULK_SELECTION:
        raise ValueError("IDs must be a non-empty list within the selection limit")
    if any(not isinstance(item, int) or isinstance(item, bool) or item < 1 for item in value):
        raise ValueError("IDs must contain positive integers")
    return list(dict.fromkeys(value))


def rename_summary(summary_id, title, database_path=None):
    with _connect(database_path) as connection:
        connection.execute(
            "UPDATE summaries SET title = ?, updated_at = ? WHERE id = ?",
            (validate_title(title), _now(), summary_id),
        )
        row = connection.execute("SELECT * FROM summaries WHERE id = ?", (summary_id,)).fetchone()
    return _record(row) if row else None


def delete_summary(summary_id, database_path=None):
    with _connect(database_path) as connection:
        return connection.execute("DELETE FROM summaries WHERE id = ?", (summary_id,)).rowcount == 1


def _selected_summaries(summary_ids, database_path=None):
    ids = validate_summary_ids(summary_ids)
    placeholders = ", ".join("?" for _ in ids)
    with _connect(database_path) as connection:
        rows = connection.execute(f"SELECT * FROM summaries WHERE id IN ({placeholders})", ids).fetchall()
    if len(rows) != len(ids):
        raise LookupError("One or more selected summaries no longer exist")
    records_by_id = {row["id"]: _record(row) for row in rows}
    return [records_by_id[summary_id] for summary_id in ids]


def bulk_delete_summaries(summary_ids, database_path=None):
    with _connect(database_path) as connection:
        ids = validate_summary_ids(summary_ids)
        placeholders = ", ".join("?" for _ in ids)
        connection.execute("BEGIN IMMEDIATE")
        rows = connection.execute(f"SELECT * FROM summaries WHERE id IN ({placeholders})", ids).fetchall()
        if len(rows) != len(ids):
            raise LookupError("One or more selected summaries no longer exist")
        deleted_count = connection.execute(f"DELETE FROM summaries WHERE id IN ({placeholders})", ids).rowcount
        if deleted_count != len(ids):
            raise LookupError("One or more selected summaries no longer exist")
    return {"deleted_ids": ids}


def markdown_filename(title, summary_id):
    slug = re.sub(r"[^A-Za-z0-9]+", "-", title).strip("-").lower() or "summary"
    return f"{slug[:80]}-{summary_id}.md"


def build_summaries_zip(summary_ids, database_path=None):
    archive = BytesIO()
    with ZipFile(archive, "w", ZIP_DEFLATED) as zip_file:
        for record in _selected_summaries(summary_ids, database_path):
            zip_file.writestr(markdown_filename(record["title"], record["id"]), record["markdown"])
    return archive.getvalue()
