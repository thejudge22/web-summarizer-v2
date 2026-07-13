from pathlib import Path
import unittest


class StealthRetryUiTests(unittest.TestCase):
    def setUp(self):
        self.template = Path("templates/loading.html").read_text()

    def test_warns_about_stealth_cost(self):
        self.assertIn("5× the standard scrape rate", self.template)

    def test_stealth_button_starts_an_explicit_stealth_stream(self):
        self.assertIn("fetchSummaryStream(true)", self.template)
        self.assertIn("stealth_mode=${stealthMode}", self.template)
