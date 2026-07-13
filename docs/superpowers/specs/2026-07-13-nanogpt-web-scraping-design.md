# NanoGPT webpage scraping and opt-in stealth mode — Design

## Goal

Replace Trafilatura webpage extraction with NanoGPT's Web Scraping API and
give users an explicit, cost-aware option to retry failed normal scrapes in
stealth mode.

## Scope

- Use `POST https://nano-gpt.com/api/scrape-urls` for non-YouTube URLs.
- Authenticate with `OPENAI_API_KEY` as the `x-api-key` header.
- Request one URL per call and return NanoGPT's `markdown` field as the
  existing `(content, "Webpage")` result.
- Apply the existing rate-limit policy: retry only HTTP 429 after 5 seconds,
  then 10 seconds, then raise after the third 429 response.
- Start with `stealthMode: false`.
- On a normal per-page scrape failure, offer the user—not the server—an
  explicit stealth retry, including a 5× cost warning.
- Remove the unused `trafilatura` dependency, add mocked tests, and update
  `README.md` and `AGENTS.md`.

## Server design

`fetch_webpage_content(url, stealth_mode=False)` will become the webpage
adapter. It validates that `OPENAI_API_KEY` is set, posts
`{"urls": [url], "stealthMode": stealth_mode}`, and returns the first result's
non-empty Markdown when `success` is true. It preserves the existing
`fetch_content(url)` contract for standard scrapes.

The adapter treats invalid or malformed payloads, empty Markdown, network
errors, non-429 HTTP errors, and failed stealth attempts as `ValueError`s.
It raises a dedicated `StealthRetryAvailableError` only when a non-stealth
request receives a well-formed per-page failure. That exception carries the
provider message and lets the streaming route distinguish an eligible retry
from a terminal error without guessing from text.

The streaming endpoint accepts an optional `stealth_mode` boolean query
parameter. On the first normal failure eligible for stealth, it emits a
`stealth_available` SSE event instead of an `error` event and closes the
stream. A request made with `stealth_mode=true` never emits that event; any
failure is terminal and uses the existing `error` event.

## Browser design

The loading page handles `stealth_available` by closing the current
`EventSource` and showing a focused recovery panel. It states that normal
scraping failed, displays NanoGPT's provider message, and makes the 5×
standard-rate cost explicit. Its “Try Stealth Mode” button opens a new stream
for the same URL with `stealth_mode=true`; its cancel option returns home. The
existing stop button, normal progress display, and standard error state remain
unchanged.

## Testing

Mocked tests will verify:

1. Standard scraping sends the exact NanoGPT endpoint, headers, one-URL
   payload, `stealthMode: false`, and timeout.
2. A successful result returns Markdown with source type `Webpage`.
3. Provider failures, malformed payloads, empty Markdown, missing credentials,
   non-429 HTTP errors, and network errors are user-safe.
4. HTTP 429 retries wait 5 then 10 seconds and fail after the third response.
5. A normal per-page failure raises `StealthRetryAvailableError`; a stealth
   per-page failure remains terminal.
6. The streaming route emits `stealth_available` only for a normal eligible
   failure and terminal `error` for a failed stealth retry.
7. Browser-script tests or focused static assertions verify the explicit cost
   warning and that a stealth retry includes `stealth_mode=true`.

## Documentation

`README.md` will describe NanoGPT webpage scraping, its $0.001 successful
standard-scrape price, and the optional 5× stealth retry. `AGENTS.md` will
describe the webpage adapter, SSE recovery event, and test command.
