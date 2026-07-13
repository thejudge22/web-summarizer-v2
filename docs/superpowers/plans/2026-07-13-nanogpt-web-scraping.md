# NanoGPT Web Scraping and Stealth Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Trafilatura webpage extraction with NanoGPT scraping and offer an explicit, cost-aware stealth retry when normal scraping fails.

**Architecture:** Keep `fetch_content()` as the source-type router. Add a NanoGPT webpage adapter that returns Markdown, follows the fixed 429 retry policy, and raises `StealthRetryAvailableError` only for a normal per-page provider failure. The SSE route maps that exception to a `stealth_available` event, and the existing loading page presents an opt-in stealth retry UI.

**Tech Stack:** Python 3.11, FastAPI, requests, unittest, Jinja2, browser EventSource API, Docker.

## Global Constraints

- Use `OPENAI_API_KEY` as NanoGPT's `x-api-key`; never log or commit the key.
- POST exactly one URL to `https://nano-gpt.com/api/scrape-urls` as `{"urls": [url], "stealthMode": stealth_mode}` with a 30-second timeout.
- Return the first successful result's non-empty `markdown` field as `(content, "Webpage")`.
- Retry only HTTP 429, waiting 5 seconds before attempt two and 10 seconds before attempt three; raise after a third 429 response.
- Normal scraping starts with `stealthMode: false`; stealth is never automatic.
- Only a normal, well-formed per-page scrape failure raises `StealthRetryAvailableError`; a stealth failure is terminal.
- The stealth offer must say it costs 5× the standard scrape rate and only retry after a user click.
- Preserve the existing YouTube path, `fetch_content()` contract, SSE event formats, and normal error behavior.
- Update both `README.md` and `AGENTS.md` in the same change set.

---

## File structure

- Modify `fetcher.py` — NanoGPT scrape adapter, retry handling, and `StealthRetryAvailableError`.
- Modify `main.py` — accepts `stealth_mode` and emits the `stealth_available` SSE event.
- Modify `templates/loading.html` — explicit stealth-cost recovery panel and retry action.
- Modify `requirements.txt` — remove `trafilatura`.
- Modify `tests/test_fetcher.py` — webpage adapter tests.
- Create `tests/test_streaming.py` — SSE event tests.
- Create `tests/test_stealth_ui.py` — browser-script content assertions.
- Modify `README.md` and `AGENTS.md` — provider, pricing, recovery, and verification documentation.

### Task 1: Replace the webpage adapter with NanoGPT scraping

**Files:**
- Modify: `fetcher.py:1-117`
- Modify: `tests/test_fetcher.py`

**Interfaces:**
- Produces: `class StealthRetryAvailableError(ValueError)`.
- Produces: `fetch_webpage_content(url: str, stealth_mode: bool = False) -> tuple[str, str]`.
- Preserves: `fetch_content(url: str) -> tuple[str, str]`.

- [ ] **Step 1: Write the failing standard-scrape contract test**

```python
from fetcher import fetch_webpage_content

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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_fetcher.FetchYouTubeTranscriptTests.test_returns_markdown_from_nanogpt_web_scrape -v`

Expected: FAIL because `fetch_webpage_content` still calls Trafilatura and does not expose the NanoGPT request seam.

- [ ] **Step 3: Implement the NanoGPT webpage adapter**

```python
NANOGPT_SCRAPE_URLS_URL = "https://nano-gpt.com/api/scrape-urls"


class StealthRetryAvailableError(ValueError):
    pass


def fetch_webpage_content(url: str, stealth_mode: bool = False) -> Tuple[str, str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set in environment variables")

    for attempt in range(3):
        try:
            response = requests.post(
                NANOGPT_SCRAPE_URLS_URL,
                json={"urls": [url], "stealthMode": stealth_mode},
                headers={"Content-Type": "application/json", "x-api-key": api_key},
                timeout=NANOGPT_REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as error:
            raise ValueError(f"Error contacting NanoGPT scraping service: {error}") from error

        if response.status_code == 429:
            if attempt == 2:
                raise ValueError("NanoGPT scraping rate limit exceeded after 3 attempts")
            time.sleep(NANOGPT_RATE_LIMIT_DELAYS_SECONDS[attempt])
            continue

        if not response.ok:
            try:
                error_body = response.json()
                message = error_body.get("error", response.text) if isinstance(error_body, dict) else response.text
            except ValueError:
                message = response.text
            raise ValueError(f"NanoGPT scraping request failed: {message}")

        try:
            result = response.json()["results"][0]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ValueError("NanoGPT returned an invalid scraping response") from error
        if not isinstance(result, dict):
            raise ValueError("NanoGPT returned an invalid scraping response")
        if not result.get("success"):
            message = result.get("error") or "NanoGPT could not scrape this page"
            if not stealth_mode:
                raise StealthRetryAvailableError(message)
            raise ValueError(message)

        markdown = result.get("markdown")
        if not isinstance(markdown, str) or not markdown.strip():
            raise ValueError("NanoGPT returned empty scraped content")
        return markdown, "Webpage"

    raise AssertionError("Unreachable retry state")
```

- [ ] **Step 4: Run the focused test to verify it passes**

Run: `python3 -m unittest tests.test_fetcher.FetchYouTubeTranscriptTests.test_returns_markdown_from_nanogpt_web_scrape -v`

Expected: PASS.

- [ ] **Step 5: Add failure and retry coverage**

```python
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
```

- [ ] **Step 6: Run the adapter suite**

Run: `python3 -m unittest tests.test_fetcher -v`

Expected: PASS with standard success, provider failure, malformed payload, empty Markdown, and 429 retry coverage.

- [ ] **Step 7: Commit**

```bash
git add fetcher.py tests/test_fetcher.py
git commit -m "feat: scrape webpages through NanoGPT"
```

### Task 2: Emit a stealth-availability SSE event

**Files:**
- Modify: `main.py:45-86`
- Create: `tests/test_streaming.py`

**Interfaces:**
- Consumes: `StealthRetryAvailableError(message)` from `fetcher.py`.
- Produces: `summary_generator(url: str, request: Request, stealth_mode: bool = False)` and `stealth_available` SSE event data `{"type": "stealth_available", "message": message}`.

- [ ] **Step 1: Write the failing SSE test**

```python
import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch

from fetcher import StealthRetryAvailableError
from main import summary_generator


class SummaryGeneratorTests(unittest.TestCase):
    @patch("main.fetch_content", side_effect=StealthRetryAvailableError("Blocked by source"))
    @patch("main.run_in_threadpool")
    def test_normal_scrape_failure_emits_stealth_available(self, run_in_threadpool, fetch_content):
        run_in_threadpool.side_effect = StealthRetryAvailableError("Blocked by source")

        request = AsyncMock()
        request.is_disconnected.return_value = False
        events = asyncio.run(self._collect(summary_generator("https://example.com", request)))

        self.assertEqual(events[-1], {"type": "stealth_available", "message": "Blocked by source"})

    async def _collect(self, generator):
        return [json.loads(event.removeprefix("data: ").strip()) async for event in generator]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_streaming.SummaryGeneratorTests.test_normal_scrape_failure_emits_stealth_available -v`

Expected: FAIL because the generator currently turns the exception into an `error` event.

- [ ] **Step 3: Thread the flag through the generator and route**

```python
from fastapi import FastAPI, Request, Query, Form

from fetcher import StealthRetryAvailableError, fetch_content, fetch_webpage_content

async def summary_generator(url: str, request: Request, stealth_mode: bool = False):
    try:
        url = clean_youtube_url(url)
        yield f"data: {json.dumps({'type': 'status', 'message': 'Fetching content...'})}\n\n"
        if stealth_mode:
            content, source_type = await run_in_threadpool(fetch_webpage_content, url, True)
        else:
            content, source_type = await run_in_threadpool(fetch_content, url)
        stream = await summarize_content_stream_async(content, source_type)
        async for chunk in stream:
            if await request.is_disconnected():
                break
            if chunk.choices[0].delta.content:
                yield f"data: {json.dumps({'type': 'content', 'chunk': chunk.choices[0].delta.content})}\n\n"
        if not await request.is_disconnected():
            yield f"data: {json.dumps({'type': 'status', 'message': 'Complete'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'source_type': source_type, 'url': url})}\n\n"
    except StealthRetryAvailableError as error:
        yield f"data: {json.dumps({'type': 'stealth_available', 'message': str(error)})}\n\n"
    except ValueError as error:
        yield f"data: {json.dumps({'type': 'error', 'message': str(error)})}\n\n"


@app.get("/api/summary/stream")
async def api_summary_stream(
    request: Request,
    url: str = Query(...),
    stealth_mode: bool = Query(False),
):
    return StreamingResponse(
        summary_generator(url, request, stealth_mode),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
```

- [ ] **Step 4: Add terminal-stealth coverage**

```python
    @patch("main.run_in_threadpool", side_effect=ValueError("Still blocked"))
    def test_stealth_scrape_failure_emits_terminal_error(self, run_in_threadpool):
        request = AsyncMock()
        request.is_disconnected.return_value = False
        events = asyncio.run(self._collect(summary_generator("https://example.com", request, True)))

        self.assertEqual(events[-1], {"type": "error", "message": "Still blocked"})
```

- [ ] **Step 5: Run SSE tests to verify they pass**

Run: `python3 -m unittest tests.test_streaming -v`

Expected: PASS; normal provider failure emits `stealth_available`, while a stealth failure emits terminal `error`.

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_streaming.py
git commit -m "feat: offer stealth retry for failed web scrapes"
```

### Task 3: Add explicit stealth-retry browser recovery

**Files:**
- Modify: `templates/loading.html:100-280`
- Create: `tests/test_stealth_ui.py`

**Interfaces:**
- Consumes: SSE `stealth_available` event with a provider message.
- Produces: a recovery panel with a user-click-only retry that calls `fetchSummaryStream(true)`.

- [ ] **Step 1: Write failing UI contract assertions**

```python
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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 -m unittest tests.test_stealth_ui -v`

Expected: FAIL because the loading page has no stealth panel or query parameter.

- [ ] **Step 3: Add the recovery panel and client behavior**

```html
<div id="stealth-container" class="fixed inset-0 bg-white flex items-center justify-center z-50 hidden">
  <div class="text-center max-w-md px-6">
    <h2 class="text-2xl font-bold text-gray-800 mb-2">This page could not be scraped</h2>
    <p id="stealth-message" class="text-gray-600 mb-4"></p>
    <p class="text-sm text-gray-500 mb-6">Stealth mode costs 5× the standard scrape rate. It will only run if you choose it.</p>
    <div class="flex gap-4">
      <button id="try-stealth-btn" class="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-6 rounded-lg">Try Stealth Mode</button>
      <a href="/" class="flex-1 bg-gray-600 hover:bg-gray-700 text-white font-semibold py-2 px-6 rounded-lg text-center">Go Back</a>
    </div>
  </div>
</div>
```

```javascript
function showStealthOption(message) {
    eventSource?.close();
    eventSource = null;
    document.getElementById('loading-container').classList.add('hidden');
    document.getElementById('stealth-container').classList.remove('hidden');
    document.getElementById('stealth-message').textContent = message;
}

document.getElementById('try-stealth-btn').addEventListener('click', function() {
    document.getElementById('stealth-container').classList.add('hidden');
    document.getElementById('loading-container').classList.remove('hidden');
    fullSummary = '';
    isStopped = false;
    fetchSummaryStream(true);
});

async function fetchSummaryStream(stealthMode = false) {
    eventSource = new EventSource(
        `/api/summary/stream?url=${encodeURIComponent(url)}&stealth_mode=${stealthMode}`
    );
    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);
        switch (data.type) {
            case 'status': updateStatus(data.message); break;
            case 'content': fullSummary += data.chunk; updateSummaryDisplay(); break;
            case 'stealth_available': showStealthOption(data.message); break;
            case 'done': eventSource.close(); eventSource = null; showResult(data.source_type, data.url); break;
            case 'error': eventSource.close(); eventSource = null; showError(data.message); break;
        }
    };
}
```

- [ ] **Step 4: Run UI tests to verify they pass**

Run: `python3 -m unittest tests.test_stealth_ui -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/loading.html tests/test_stealth_ui.py
git commit -m "feat: add opt-in stealth scrape recovery"
```

### Task 4: Update dependencies, documentation, and full verification

**Files:**
- Modify: `requirements.txt`
- Modify: `README.md`
- Modify: `AGENTS.md`

**Interfaces:**
- Consumes: complete NanoGPT webpage adapter and stealth recovery behavior.
- Produces: reproducible installation and accurate user/developer guidance.

- [ ] **Step 1: Remove Trafilatura from runtime dependencies**

```text
Remove: trafilatura
```

- [ ] **Step 2: Document normal and stealth scraping**

Add this exact README text near the existing NanoGPT section:

```markdown
Webpage summaries use NanoGPT's Web Scraping API. Standard successful scrapes cost $0.001 per URL. If a normal scrape fails, the app can offer an explicit stealth-mode retry; stealth mode costs 5× the standard scrape rate and is never enabled automatically.
```

- [ ] **Step 3: Update the developer guide**

Add to `AGENTS.md`: `Non-YouTube URLs are fetched through NanoGPT's scrape-urls endpoint. Normal per-page failures emit the stealth_available SSE event; only a user click may retry with stealth_mode=true.`

- [ ] **Step 4: Run final verification**

Run: `python3 -m unittest discover -s tests -v && python3 -m py_compile main.py fetcher.py summarizer.py && git diff --check`

Expected: all tests pass, compilation succeeds, and no whitespace errors appear.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt README.md AGENTS.md
git commit -m "docs: document NanoGPT web scraping"
```
