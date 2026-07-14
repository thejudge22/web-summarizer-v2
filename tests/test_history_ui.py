from pathlib import Path
import unittest


class HistoryUiTests(unittest.TestCase):
    def test_shared_shell_includes_sidebar_and_controller(self):
        template = Path("templates/base.html").read_text()

        self.assertIn('{% include "history_sidebar.html" %}', template)
        self.assertIn('/static/history.js', template)

    def test_controller_contains_bulk_and_single_delete_behavior(self):
        script = Path("static/history.js").read_text()

        self.assertIn("/api/summaries", script)
        self.assertIn("bulk-delete", script)
        self.assertIn("download-zip", script)
        self.assertIn("confirm(", script)

    def test_saved_summary_url_is_protocol_checked_before_linking(self):
        template = Path("templates/index.html").read_text()

        self.assertIn("isSafeExternalUrl", template)
