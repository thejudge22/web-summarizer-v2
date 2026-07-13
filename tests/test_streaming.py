import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch

from fetcher import StealthRetryAvailableError
from main import fetch_content, fetch_webpage_content, summary_generator


class SummaryGeneratorTests(unittest.TestCase):
    @patch("main.fetch_content", side_effect=StealthRetryAvailableError("Blocked by source"))
    @patch("main.run_in_threadpool")
    def test_normal_scrape_failure_emits_stealth_available(self, run_in_threadpool, fetch_content):
        run_in_threadpool.side_effect = StealthRetryAvailableError("Blocked by source")

        request = AsyncMock()
        request.is_disconnected.return_value = False
        events = asyncio.run(self._collect(summary_generator("https://example.com", request)))

        self.assertEqual(events[-1], {"type": "stealth_available", "message": "Blocked by source"})

    @patch("main.run_in_threadpool", side_effect=ValueError("Still blocked"))
    def test_stealth_scrape_failure_emits_terminal_error(self, run_in_threadpool):
        request = AsyncMock()
        request.is_disconnected.return_value = False
        events = asyncio.run(self._collect(summary_generator("https://example.com", request, True)))

        self.assertEqual(events[-1], {"type": "error", "message": "Still blocked"})

    @patch("main.run_in_threadpool", side_effect=ValueError("Still blocked"))
    def test_stealth_webpage_scrape_uses_stealth_fetcher(self, run_in_threadpool):
        request = AsyncMock()
        request.is_disconnected.return_value = False

        asyncio.run(self._collect(summary_generator("https://example.com", request, True)))

        run_in_threadpool.assert_called_once_with(fetch_webpage_content, "https://example.com", True)

    @patch("main.fetch_webpage_content")
    @patch("main.run_in_threadpool", side_effect=ValueError("Still blocked"))
    def test_stealth_youtube_scrape_uses_normal_fetcher(self, run_in_threadpool, fetch_webpage_content):
        request = AsyncMock()
        request.is_disconnected.return_value = False
        url = "https://youtu.be/abc123?feature=share"

        asyncio.run(self._collect(summary_generator(url, request, True)))

        run_in_threadpool.assert_called_once_with(
            fetch_content,
            "https://www.youtube.com/watch?v=abc123",
        )
        fetch_webpage_content.assert_not_called()

    async def _collect(self, generator):
        return [json.loads(event.removeprefix("data: ").strip()) async for event in generator]
