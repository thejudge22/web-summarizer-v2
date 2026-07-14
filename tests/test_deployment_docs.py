from pathlib import Path
import unittest


class DeploymentDocumentationTests(unittest.TestCase):
    def test_compose_example_mounts_data_directory(self):
        compose = Path("docker-compose-example.yml").read_text()
        self.assertIn("./data:/app/data", compose)
        self.assertIn("SUMMARY_DATA_DIR=/app/data", compose)

    def test_readme_documents_history_and_database_path(self):
        readme = Path("README.md").read_text()
        self.assertIn("Saved Summary History", readme)
        self.assertIn("docker-compose-example.yml", readme)
        self.assertIn("data/summaries.db", readme)
