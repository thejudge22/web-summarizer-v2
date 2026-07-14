import tempfile
import unittest
import sqlite3
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from storage import (
    build_summaries_zip,
    _connect,
    bulk_delete_summaries,
    create_summary,
    delete_summary,
    get_summary,
    initialize_database,
    list_summaries,
    markdown_filename,
    rename_summary,
    validate_summary_ids,
    validate_title,
)


class SummaryStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "summaries.db"
        initialize_database(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_creates_and_lists_metadata_newest_first(self):
        first = create_summary("📝 First saved summary", "https://first.example", "Webpage", "# First", self.path)
        second = create_summary("🎥 Second saved summary", "https://second.example", "YouTube", "# Second", self.path)

        self.assertEqual(get_summary(first["id"], self.path)["markdown"], "# First")
        records = list_summaries(self.path)
        self.assertEqual([record["id"] for record in records], [second["id"], first["id"]])
        self.assertEqual(records[0]["source_host"], "second.example")
        self.assertNotIn("markdown", records[0])

    def test_rename_delete_and_validation(self):
        record = create_summary("📝 Original title", "https://example.com", "Webpage", "body", self.path)
        self.assertEqual(rename_summary(record["id"], "🧾 Renamed summary", self.path)["title"], "🧾 Renamed summary")
        self.assertTrue(delete_summary(record["id"], self.path))
        self.assertFalse(delete_summary(record["id"], self.path))
        with self.assertRaises(ValueError):
            validate_title("   ")
        with self.assertRaises(ValueError):
            validate_summary_ids([1, "bad"])

    def test_zip_has_one_safe_markdown_file_per_selected_summary(self):
        first = create_summary("🚀 A/B launch plan", "https://a.example", "Webpage", "# A", self.path)
        second = create_summary("🎥 Video key points", "https://b.example", "YouTube", "# B", self.path)
        with ZipFile(BytesIO(build_summaries_zip([first["id"], second["id"]], self.path))) as archive:
            self.assertEqual(archive.read(markdown_filename(first["title"], first["id"])).decode(), "# A")
            self.assertEqual(len(archive.namelist()), 2)
        self.assertEqual(bulk_delete_summaries([first["id"], second["id"]], self.path)["deleted_ids"], [first["id"], second["id"]])

    def test_bulk_delete_rolls_back_when_not_every_selected_record_is_deleted(self):
        first = create_summary("First", "https://first.example", "Webpage", "# First", self.path)
        second = create_summary("Second", "https://second.example", "Webpage", "# Second", self.path)
        with _connect(self.path) as connection:
            connection.execute(
                f"CREATE TRIGGER remove_second_selected_summary "
                f"BEFORE DELETE ON summaries "
                f"WHEN OLD.id = {first['id']} "
                f"BEGIN DELETE FROM summaries WHERE id = {second['id']}; END"
            )

        with self.assertRaises(LookupError):
            bulk_delete_summaries([first["id"], second["id"]], self.path)

        self.assertIsNotNone(get_summary(first["id"], self.path))
        self.assertIsNotNone(get_summary(second["id"], self.path))

    def test_database_connection_is_closed_after_use(self):
        with _connect(self.path) as connection:
            connection.execute("SELECT 1")

        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")
