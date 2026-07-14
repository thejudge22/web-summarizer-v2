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

    @patch("main.create_summary", return_value={"id": 7})
    @patch("main.generate_summary_title", new_callable=AsyncMock, return_value="🧠 SQLite summary history")
    @patch("main.summarize_content_stream_async")
    @patch("main.run_in_threadpool", new_callable=AsyncMock)
    def test_completed_stream_saves_accumulated_markdown(self, threadpool, stream_function, title_function, create_summary):
        request = AsyncMock()
        request.is_disconnected.return_value = False
        threadpool.side_effect = [("source", "Webpage"), {"id": 7}]
        stream_function.return_value = self._stream("# Result", " body")

        events = asyncio.run(self._collect(summary_generator("https://example.com", request)))

        title_function.assert_awaited_once_with("# Result body")
        self.assertEqual(
            threadpool.call_args_list[1].args,
            (create_summary, "🧠 SQLite summary history", "https://example.com", "Webpage", "# Result body"),
        )
        self.assertEqual(events[-1]["summary_id"], 7)
        self.assertEqual(events[-1]["title"], "🧠 SQLite summary history")

    @patch("main.create_summary")
    @patch("main.summarize_content_stream_async")
    @patch("main.run_in_threadpool", new_callable=AsyncMock)
    def test_disconnected_stream_is_not_saved(self, threadpool, stream_function, create_summary):
        request = AsyncMock()
        request.is_disconnected.side_effect = [False, True]
        threadpool.return_value = ("source", "Webpage")
        stream_function.return_value = self._stream("partial")

        asyncio.run(self._collect(summary_generator("https://example.com", request)))

        create_summary.assert_not_called()
        self.assertEqual(threadpool.await_count, 1)

    @patch("main.create_summary")
    @patch("main.generate_summary_title", new_callable=AsyncMock, return_value="A completed summary")
    @patch("main.summarize_content_stream_async")
    @patch("main.run_in_threadpool", new_callable=AsyncMock)
    def test_stream_disconnected_while_generating_title_is_not_saved(
        self, threadpool, stream_function, title_function, create_summary
    ):
        request = AsyncMock()
        request.is_disconnected.side_effect = [False, False, True]
        threadpool.return_value = ("source", "Webpage")
        stream_function.return_value = self._stream("complete")

        events = asyncio.run(self._collect(summary_generator("https://example.com", request)))

        title_function.assert_awaited_once_with("complete")
        create_summary.assert_not_called()
        self.assertEqual(threadpool.await_count, 1)
        self.assertEqual(events[-1]["type"], "status")

    @patch("main.create_summary", return_value={"id": 8})
    @patch("main.generate_summary_title", new_callable=AsyncMock, side_effect=ValueError("bad title"))
    @patch("main.summarize_content_stream_async")
    @patch("main.run_in_threadpool", new_callable=AsyncMock)
    def test_title_failure_saves_with_fallback(self, threadpool, stream_function, title_function, create_summary):
        request = AsyncMock()
        request.is_disconnected.return_value = False
        threadpool.side_effect = [("source", "Webpage"), {"id": 8}]
        stream_function.return_value = self._stream("complete")

        events = asyncio.run(self._collect(summary_generator("https://example.com", request)))

        self.assertEqual(
            threadpool.call_args_list[1].args,
            (create_summary, "📝 Untitled summary", "https://example.com", "Webpage", "complete"),
        )
        self.assertEqual(events[-1]["title"], "📝 Untitled summary")

    @patch("main.create_summary", side_effect=OSError("disk full"))
    @patch("main.generate_summary_title", new_callable=AsyncMock, return_value="📝 Complete summary")
    @patch("main.summarize_content_stream_async")
    @patch("main.run_in_threadpool", new_callable=AsyncMock)
    def test_storage_failure_completes_without_saved_identifier(self, threadpool, stream_function, title_function, create_summary):
        request = AsyncMock()
        request.is_disconnected.return_value = False
        threadpool.side_effect = [("source", "Webpage"), OSError("disk full")]
        stream_function.return_value = self._stream("complete")

        events = asyncio.run(self._collect(summary_generator("https://example.com", request)))

        self.assertIsNone(events[-1]["summary_id"])
        self.assertIn("could not be saved", events[-1]["save_error"])

    async def _collect(self, generator):
        return [json.loads(event.removeprefix("data: ").strip()) async for event in generator]

    async def _stream(self, *chunks):
        for chunk in chunks:
            yield type("Chunk", (), {"choices": [type("Choice", (), {"delta": type("Delta", (), {"content": chunk})()})()]})()
