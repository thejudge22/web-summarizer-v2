# NanoGPT YouTube transcript integration — Design

## Goal

Replace the local `youtube-transcript-api` integration with NanoGPT's YouTube
Transcription API while preserving the application's existing single-URL,
streaming summary flow.

## Scope

- Send each cleaned YouTube URL to `POST https://nano-gpt.com/api/youtube-transcribe`.
- Authenticate with `OPENAI_API_KEY` as the `x-api-key` header.
- Read the first result in the API's `transcripts` array and keep the existing
  `(transcript, "YouTube")` return contract.
- Retry HTTP 429 responses after 5 seconds and then 10 seconds. Raise a
  user-facing error if the third request still fails.
- Replace the unused YouTube transcript library dependency with `requests`.
- Add mocked tests for successful results, provider-reported failures, retry
  behavior, and retry exhaustion.
- Update `README.md` and `AGENTS.md` with the provider/dependency change.

## Design

`fetch_youtube_transcript(url)` remains the sole YouTube-specific integration
point. It will validate and clean the URL using the existing helpers, load the
API key from the environment, then issue a JSON request containing one URL.
The function will use a finite timeout so an unavailable provider cannot block
a worker indefinitely.

For a successful HTTP response, it will validate that the payload contains a
transcript result. A result whose `success` value is true must include usable
transcript text and returns that text with source type `YouTube`. A failed
result raises the provider's error message, or a stable fallback message when
the response lacks one. Malformed success payloads and non-429 HTTP/network
errors become clear `ValueError` messages, which existing routes already send
to the browser error state.

For an HTTP 429 response, the client will wait 5 seconds before the second
attempt and 10 seconds before the third attempt. It will make no further
request after that third attempt. Other status codes do not retry. This bounds
latency and avoids accidental repeated charges while handling transient rate
limits.

The URL-cleaning behavior, server-sent-event schema, summary prompt selection,
UI, and public routes remain unchanged.

## Testing

Tests will mock outbound HTTP and sleep calls. They will cover:

1. A successful NanoGPT response returns the transcript and `YouTube` type.
2. A per-transcript provider failure raises its message.
3. A 429 followed by success sleeps for 5 seconds and succeeds.
4. Two 429s followed by success sleep for 5 and 10 seconds.
5. Three 429s raise a rate-limit error after the two specified waits.
6. Missing credentials, malformed JSON/payloads, and non-429 HTTP errors are
   surfaced safely.

## Documentation

`README.md` will state that YouTube transcripts are obtained through NanoGPT
using the existing API key. `AGENTS.md` will update the fetching/dependency
description and verification baseline to include the test command.
