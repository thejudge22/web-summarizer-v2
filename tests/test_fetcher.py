import os
import unittest
from unittest.mock import Mock, call, patch

from fetcher import StealthRetryAvailableError, fetch_webpage_content, fetch_youtube_transcript


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

    @patch("fetcher.requests.post")
    def test_returns_markdown_from_nanogpt_web_scrape(self, post):
        response = Mock(status_code=200, ok=True)
        response.json.return_value = {
            "results": [{"success": True, "markdown": "# Article\n\nBody"}]
        }
        post.return_value = response

        self.assertEqual(
            fetch_webpage_content("https://example.com/article"),
            ("# Article\n\nBody", "Webpage"),
        )
        post.assert_called_once_with(
            "https://nano-gpt.com/api/scrape-urls",
            json={"urls": ["https://example.com/article"], "stealthMode": False},
            headers={"Content-Type": "application/json", "x-api-key": "test-key"},
            timeout=30,
        )

    @patch("fetcher.time.sleep")
    @patch("fetcher.requests.post")
    def test_web_scrape_retries_rate_limit_after_five_then_ten_seconds(self, post, sleep):
        limited = Mock(status_code=429)
        success = Mock(status_code=200, ok=True)
        success.json.return_value = {"results": [{"success": True, "markdown": "Recovered"}]}
        post.side_effect = [limited, limited, success]

        self.assertEqual(fetch_webpage_content("https://example.com"), ("Recovered", "Webpage"))
        self.assertEqual(sleep.call_args_list, [call(5), call(10)])

    @patch("fetcher.requests.post")
    def test_normal_scrape_failure_offers_stealth_retry(self, post):
        response = Mock(status_code=200, ok=True)
        response.json.return_value = {"results": [{"success": False, "error": "Blocked"}]}
        post.return_value = response

        with self.assertRaisesRegex(StealthRetryAvailableError, "Blocked"):
            fetch_webpage_content("https://example.com")

    @patch("fetcher.requests.post")
    def test_stealth_scrape_failure_is_terminal(self, post):
        response = Mock(status_code=200, ok=True)
        response.json.return_value = {"results": [{"success": False, "error": "Still blocked"}]}
        post.return_value = response

        with self.assertRaisesRegex(ValueError, "Still blocked"):
            fetch_webpage_content("https://example.com", stealth_mode=True)

    @patch("fetcher.requests.post")
    def test_rejects_malformed_web_scrape_response(self, post):
        response = Mock(status_code=200, ok=True)
        response.json.return_value = {"results": []}
        post.return_value = response

        with self.assertRaisesRegex(ValueError, "invalid scraping response"):
            fetch_webpage_content("https://example.com")

    @patch("fetcher.requests.post")
    def test_rejects_empty_scraped_markdown(self, post):
        response = Mock(status_code=200, ok=True)
        response.json.return_value = {"results": [{"success": True, "markdown": "  "}]}
        post.return_value = response

        with self.assertRaisesRegex(ValueError, "empty scraped content"):
            fetch_webpage_content("https://example.com")

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

    @patch("fetcher.requests.post")
    def test_raises_provider_transcript_error(self, post):
        response = Mock(status_code=200, ok=True)
        response.json.return_value = {
            "transcripts": [{"success": False, "error": "Captions unavailable"}]
        }
        post.return_value = response

        with self.assertRaisesRegex(ValueError, "Captions unavailable"):
            fetch_youtube_transcript("https://www.youtube.com/watch?v=abc123")

    @patch("fetcher.time.sleep")
    @patch("fetcher.requests.post")
    def test_retries_429_after_five_then_ten_seconds(self, post, sleep):
        limited = Mock(status_code=429)
        successful = Mock(status_code=200, ok=True)
        successful.json.return_value = {
            "transcripts": [{"success": True, "transcript": "Recovered"}]
        }
        post.side_effect = [limited, limited, successful]

        self.assertEqual(
            fetch_youtube_transcript("https://www.youtube.com/watch?v=abc123"),
            ("Recovered", "YouTube"),
        )
        self.assertEqual(sleep.call_args_list, [call(5), call(10)])

    @patch("fetcher.time.sleep")
    @patch("fetcher.requests.post")
    def test_raises_after_third_429(self, post, sleep):
        post.return_value = Mock(status_code=429)

        with self.assertRaisesRegex(ValueError, "rate limit exceeded after 3 attempts"):
            fetch_youtube_transcript("https://www.youtube.com/watch?v=abc123")

        self.assertEqual(sleep.call_args_list, [call(5), call(10)])
        self.assertEqual(post.call_count, 3)
