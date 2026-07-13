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

    @patch("fetcher.requests.post")
    def test_rejects_non_object_transcript_entry(self, post):
        response = Mock(status_code=200, ok=True)
        response.json.return_value = {"transcripts": [None]}
        post.return_value = response

        with self.assertRaisesRegex(ValueError, "NanoGPT returned an invalid transcription response"):
            fetch_youtube_transcript("https://youtu.be/abc123")

    @patch("fetcher.requests.post")
    def test_uses_response_text_for_non_object_error_json(self, post):
        response = Mock(status_code=400, ok=False, text="Invalid request")
        response.json.return_value = []
        post.return_value = response

        with self.assertRaisesRegex(ValueError, "NanoGPT transcription request failed: Invalid request"):
            fetch_youtube_transcript("https://youtu.be/abc123")
