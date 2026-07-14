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

    def test_history_actions_use_visible_named_controls_instead_of_action_prompt(self):
        script = Path("static/history.js").read_text()

        self.assertIn("history-action-menu", script)
        self.assertIn('"Rename"', script)
        self.assertIn('"Download Markdown"', script)
        self.assertIn('"Delete"', script)
        self.assertNotIn('Type rename, download, or delete', script)

    def test_loading_overlays_leave_the_mobile_history_sidebar_reachable(self):
        base = Path("templates/base.html").read_text()
        loading = Path("templates/loading.html").read_text()

        self.assertIn('id="main-panel" class="relative min-h-screen', base)
        self.assertGreaterEqual(loading.count('class="absolute inset-0 z-50'), 4)
        self.assertNotIn('class="fixed inset-0 z-50', loading)

    def test_saved_summary_url_is_protocol_checked_before_linking(self):
        template = Path("templates/index.html").read_text()

        self.assertIn("isSafeExternalUrl", template)

    def test_desktop_overlays_are_scoped_to_the_main_panel(self):
        base = Path("templates/base.html").read_text()
        loading = Path("templates/loading.html").read_text()

        self.assertIn('id="main-panel" class="relative', base)
        self.assertGreaterEqual(loading.count("absolute inset-0 z-50"), 4)
        self.assertIn("showError(message)", loading)
        self.assertIn("getElementById('error-container').classList.add('flex')", loading)

    def test_markdown_uses_a_strict_dompurify_policy_for_hostile_markup(self):
        base = Path("templates/base.html").read_text()
        templates = [Path("templates/index.html").read_text(), Path("templates/loading.html").read_text()]
        hostile_payloads = [
            '<svg><script>alert(1)</script></svg>',
            '<math><mi xlink:href="javascript:alert(1)">x</mi></math>',
            '<a href="javascript:alert(1)">unsafe</a>',
        ]

        self.assertIn("dompurify", base.lower())
        self.assertIn("FORBID_TAGS", base)
        self.assertIn("svg", base)
        self.assertIn("math", base)
        self.assertIn("xlink", base)
        for template in templates:
            self.assertIn("DOMPurify.sanitize", template)
        self.assertTrue(all("javascript:" in payload or "<svg" in payload or "<math" in payload for payload in hostile_payloads))
