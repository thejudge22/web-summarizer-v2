import os
import unittest
from unittest.mock import Mock, call, patch

from fetcher import fetch_youtube_transcript


class FetchYouTubeTranscriptTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)

    @patch("fetcher.requests.post")
    def test_returns_nanogpt_transcript(self, post):
        response = Mock(status_code=200, ok=True)
        response.json.return_value = {
            "transcripts": [{"success": True, "transcript": "Complete transcript."}]
        }
        post.return_value = response

        self.assertEqual(
            fetch_youtube_transcript("https://youtu.be/abc123"),
            ("Complete transcript.", "YouTube"),
        )
        post.assert_called_once_with(
            "https://nano-gpt.com/api/youtube-transcribe",
            json={"urls": ["https://www.youtube.com/watch?v=abc123"]},
            headers={"Content-Type": "application/json", "x-api-key": "test-key"},
            timeout=30,
        )

    def test_requires_openai_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "OPENAI_API_KEY not set"):
                fetch_youtube_transcript("https://www.youtube.com/watch?v=abc123")
