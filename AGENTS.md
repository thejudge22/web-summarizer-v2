# Web Summarizer — Project Guide

## Purpose

Web Summarizer is a FastAPI application that fetches webpage text through
NanoGPT or retrieves YouTube transcripts, sends the extracted content to an
OpenAI-compatible API, and streams the generated Markdown summary to a browser
UI.

## Project layout

- `main.py` — FastAPI routes, server-sent-event streaming, and download
  endpoints.
- `fetcher.py` — non-YouTube webpage scraping through NanoGPT's Web Scraping
  API and YouTube transcript retrieval through NanoGPT's YouTube Transcription
  API/URL cleanup.
- `summarizer.py` — OpenAI and AsyncOpenAI client setup, prompt loading, and
  summary generation.
- `templates/index.html` — URL-entry page and bookmarklet.
- `templates/loading.html` — streaming summary UI, cancellation, Markdown
  rendering, and downloads.
- `templates/result.html` — older non-streaming result template; there is no
  active route that renders it.
- `page-summary.md` and `youtube.md` — source-specific system prompts.
- `requirements.txt`, `Dockerfile`, and `docker-compose.yml` — runtime and
  container configuration.

## Runtime behavior

1. The browser submits a URL to `/summary`.
2. The page opens an SSE connection to `/api/summary/stream`.
3. The server identifies YouTube URLs, fetches a transcript or scrapes
   non-YouTube webpages through NanoGPT, then streams the model response.
4. The browser progressively renders Markdown and offers summary/transcript
   downloads when generation completes. Only a fully completed, connected
   stream generates a summary-derived title and saves the accumulated Markdown.
   A title-generation failure uses `DEFAULT_TITLE_FALLBACK`; a storage failure
   still finishes the stream with a usable download.

### Completed-stream save metadata

- The final `done` SSE event for a completed stream contains `summary_id` and
  `title`.
- A storage failure sets `summary_id` to `null` and adds `save_error`; it does
  not turn an otherwise completed stream into an `error` event.
- Failed, cancelled, stealth-retry, and disconnected attempts must not be
  persisted. Recheck disconnect state after title generation and before storage.

### Streaming retry behavior

- Non-YouTube URLs are fetched through NanoGPT's scrape-urls endpoint. Normal
  per-page failures emit the stealth_available SSE event; only a user click may
  retry with stealth_mode=true.
- `/api/summary/stream` accepts an optional `stealth_mode=true` query parameter
  for an explicit webpage retry. This mode calls the webpage scraper with its
  stealth option, but YouTube URLs always continue through transcript routing.
- A normal webpage scrape that can be retried with stealth emits
  `{"type": "stealth_available", "message": "..."}` and ends the SSE stream.
  Explicit stealth failures remain terminal `error` events.

## Configuration

Copy `.env.example` to `.env` and set:

- `OPENAI_API_KEY` — required API key, also used as the NanoGPT API key for
  webpage scraping and YouTube transcripts. Successful NanoGPT requests are
  billed by NanoGPT.
- `OPENAI_BASE_URL` — optional OpenAI-compatible base URL.
- `OPENAI_MODEL` — optional model name.

Run locally with `python3 main.py` after installing `requirements.txt`, or use
`docker-compose up --build`.

## Working conventions

- Preserve the streaming API event format (`status`, `content`, `done`,
  `stealth_available`, and `error`) unless the client and server are updated
  together.
- Keep source-type behavior aligned across URL handling, fetching, prompts, and
  the UI.
- Do not commit `.env` or generated `summary.md` files.
- The current working tree contains executable-bit-only changes to existing
  tracked files. Preserve them unless intentionally correcting file modes.

## Documentation requirement

Every functional, configuration, API, UI, or deployment change must be
documented in **either this file or `README.md`** in the same change set:

- Update `README.md` for user-facing setup, usage, configuration, or feature
  changes.
- Update this file for implementation layout, developer workflow, architecture,
  or maintenance conventions.
- Update both when a change affects both audiences.

## Verification baseline

At minimum, run `python3 -m py_compile main.py fetcher.py summarizer.py`.
Run `python3 -m unittest tests.test_fetcher -v` after installing dependencies
to verify the NanoGPT adapter without live API calls. Run
`python3 -m unittest tests.test_templates -v` to verify the template routes use
the request-first Starlette API required by current container dependencies.
Before committing a complete change, run
`python3 -m unittest discover -s tests -v && python3 -m py_compile main.py fetcher.py summarizer.py && git diff --check`.
