import unittest
from unittest.mock import ANY, patch

from fastapi.testclient import TestClient

from main import app


class SummaryHistoryApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("main.list_summaries", return_value=[{"id": 1, "title": "🧠 SQLite history", "source_host": "example.com"}])
    def test_lists_history_metadata(self, list_summaries):
        response = self.client.get("/api/summaries")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["summaries"][0]["id"], 1)
        list_summaries.assert_called_once_with()

    @patch("main.get_summary", return_value=None)
    def test_missing_summary_is_not_found(self, get_summary):
        self.assertEqual(self.client.get("/api/summaries/999").status_code, 404)
        get_summary.assert_called_once_with(999)

    @patch("main.rename_summary", return_value={"id": 1, "title": "📝 Renamed summary"})
    def test_renames_summary(self, rename_summary):
        response = self.client.patch("/api/summaries/1", json={"title": "📝 Renamed summary"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "📝 Renamed summary")
        rename_summary.assert_called_once_with(1, "📝 Renamed summary")

    @patch("main.rename_summary", side_effect=ValueError("A title is required"))
    def test_rename_validation_error_is_unprocessable(self, rename_summary):
        response = self.client.patch("/api/summaries/1", json={"title": ""})

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "A title is required")

    @patch("main.delete_summary", return_value=True)
    def test_deletes_summary(self, delete_summary):
        response = self.client.delete("/api/summaries/1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"deleted_ids": [1]})
        delete_summary.assert_called_once_with(1)

    @patch("main.delete_summary", return_value=False)
    def test_missing_summary_delete_is_not_found(self, delete_summary):
        self.assertEqual(self.client.delete("/api/summaries/999").status_code, 404)
        delete_summary.assert_called_once_with(999)

    @patch("main.bulk_delete_summaries", return_value={"deleted_ids": [1, 2]})
    def test_bulk_delete_returns_deleted_ids(self, bulk_delete_summaries):
        response = self.client.post("/api/summaries/bulk-delete", json={"ids": [1, 2]})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"deleted_ids": [1, 2]})
        bulk_delete_summaries.assert_called_once_with([1, 2])

    def test_bulk_delete_validation_error_is_unprocessable(self):
        response = self.client.post("/api/summaries/bulk-delete", json={"ids": []})

        self.assertEqual(response.status_code, 422)

    @patch("main.bulk_delete_summaries", side_effect=LookupError("One or more selected summaries no longer exist"))
    def test_bulk_delete_missing_selection_is_not_found(self, bulk_delete_summaries):
        response = self.client.post("/api/summaries/bulk-delete", json={"ids": [1, 2]})

        self.assertEqual(response.status_code, 404)

    @patch("main.get_summary", return_value={"id": 1, "title": "🧠 History", "markdown": "# Summary"})
    def test_download_returns_markdown_attachment(self, get_summary):
        response = self.client.get("/api/summaries/1/download")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "# Summary")
        self.assertEqual(response.headers["content-type"], "text/markdown; charset=utf-8")
        self.assertIn('filename="history-1.md"', response.headers["content-disposition"])
        get_summary.assert_called_once_with(1)

    @patch("main.build_summaries_zip", return_value=b"PK\x03\x04")
    def test_bulk_download_returns_zip(self, build_summaries_zip):
        response = self.client.post("/api/summaries/download-zip", json={"ids": [1, 2]})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/zip")
        self.assertEqual(response.content, b"PK\x03\x04")
        build_summaries_zip.assert_called_once_with([1, 2])

    def test_bulk_download_validation_error_is_unprocessable(self):
        response = self.client.post("/api/summaries/download-zip", json={"ids": []})

        self.assertEqual(response.status_code, 422)

    @patch("main.build_summaries_zip", side_effect=LookupError("One or more selected summaries no longer exist"))
    def test_bulk_download_missing_selection_is_not_found(self, build_summaries_zip):
        response = self.client.post("/api/summaries/download-zip", json={"ids": [1, 2]})

        self.assertEqual(response.status_code, 404)
