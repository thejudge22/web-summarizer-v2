# Summary History Design

**Date:** 2026-07-14  
**Status:** Approved for implementation

## Goal

Persist completed webpage and YouTube summaries in a local SQLite database and provide a simple, chat-style history experience. Users can reach history from the home page and while a new summary is running, open a saved summary in the main panel, rename or delete it, and download one or several summaries as Markdown.

The application remains localhost-only and does not add authentication or multi-user isolation.

## Scope

### Included

- A persistent SQLite database in an application data directory.
- A sidebar shared by the home, new-summary, and saved-summary views.
- Saving only successfully completed summaries.
- An AI-generated title based on the completed Markdown summary: five to seven words, with a leading emoji when it is warranted.
- Per-summary rename, delete-with-confirmation, and Markdown download actions.
- Selection mode for bulk ZIP download and bulk deletion.
- A Docker Compose example that bind-mounts a local `data` directory.
- Tests and documentation for the new behavior.

### Excluded

- User accounts, authentication, sharing, sync, or remote access.
- Persisting source transcripts or webpage extraction payloads.
- Saving cancelled, failed, or stealth-retry-pending summaries.
- Search, tags, folders, and pagination. These can be added later if the history grows large.

## Architecture

### Data location and deployment

The app will use a configurable data directory, defaulting to `data` for local runs and `/app/data` in the container. SQLite will live at `<data-directory>/summaries.db`.

`docker-compose-example.yml` will show a host bind mount:

```yaml
volumes:
  - ./data:/app/data
```

This preserves history across container rebuilds and keeps the database in a visible, backup-friendly project subfolder. The README will document the same mount and warn users not to commit `data/summaries.db`.

### Persistence boundary

Add a focused `storage.py` module. It owns database setup and parameterized SQLite queries; FastAPI routes and the streaming generator use its small, explicit operations rather than writing SQL inline. Each operation uses a short-lived connection, enables the appropriate SQLite pragmas, and commits mutations in transactions.

The initial `summaries` table contains:

| Field | Purpose |
| --- | --- |
| `id` | Internal integer primary key |
| `title` | AI-generated default or user-renamed title |
| `source_url` | Cleaned source URL |
| `source_type` | Existing webpage or YouTube source type |
| `markdown` | Completed generated Markdown summary |
| `created_at` | UTC creation timestamp |
| `updated_at` | UTC timestamp updated on rename |

The list API returns metadata and a short source-hostname display value, not the Markdown body. A detail API returns the entire saved record.

### Save lifecycle

The streaming generator continues to emit content as it does today while also accumulating the Markdown server-side. Once the model stream completes and the client remains connected:

1. The server emits a saving status.
2. It asks the configured OpenAI-compatible model for a concise title from the completed Markdown.
3. It inserts the resulting title, source metadata, and Markdown in one SQLite transaction.
4. It emits the existing `done` SSE event, extended with the saved summary ID and title.

The browser therefore treats the finished result as saved only after it receives `done`. The existing event names (`status`, `content`, `done`, `stealth_available`, and `error`) remain unchanged.

If title generation fails, the app saves the completed summary with a clear, safe fallback title such as `📝 Untitled summary`. If database persistence fails, the completed result remains visible and downloadable, but the UI shows a non-blocking failure notice and does not claim the summary was saved. The server must not persist a cancelled, failed, disconnected, or stealth-retry attempt.

## Interface

### Shared shell

The home and summary templates become a shared responsive shell:

- A left history sidebar on desktop, visible by default even for a direct or bookmarklet-launched `/summary` page.
- A collapse control on smaller screens.
- A `New summary` action that returns the main panel to the URL-entry form.
- A main panel that shows one of three states: the home form, a live summary, or a saved summary.

The history list is ordered newest first. Every row presents the title, a source hostname, and a relative timestamp. Selecting a row loads the saved Markdown into the main panel without fetching the source or invoking the model again, and updates the browser URL to a stable saved-summary route.

### Item actions

Each row provides an overflow menu with:

- **Rename** — inline or small-dialog text input; the server validates a non-empty bounded title and records `updated_at`.
- **Download Markdown** — downloads the stored Markdown using a sanitized, title-derived filename.
- **Delete** — requires a single-item confirmation dialog before removal.

The saved-summary main panel also exposes equivalent actions so a user does not need to find the row menu again.

### Selection mode and bulk actions

Selection mode shows a checkbox for each visible history row and a compact bulk-action bar with the selected count.

- **Download ZIP** returns one ZIP archive containing one sanitized title-derived `.md` file per selected summary.
- **Delete selected** deletes all selected rows without an additional confirmation, by explicit product decision.

The UI must clear or accurately reconcile selection after actions and report any partial bulk-operation failures. The server validates selected IDs and a reasonable maximum selection size to keep ZIP generation bounded.

## HTTP contract

The exact route names may be finalized in the implementation plan, but the feature needs these capabilities:

| Operation | Behavior |
| --- | --- |
| List summaries | Returns newest-first metadata for the sidebar |
| Get summary | Returns one saved record including Markdown |
| Rename summary | Validates and updates the title |
| Delete summary | Removes one record |
| Bulk delete | Removes a validated list of records and reports results |
| Download Markdown | Returns one saved Markdown file |
| Download ZIP | Returns one ZIP of selected saved Markdown files |

Routes accept only internal numeric IDs. Missing records return a structured not-found response; malformed IDs, invalid rename values, or invalid bulk payloads return structured validation responses. SQL is always parameterized, and all filenames are sanitized before an attachment is generated.

## Compatibility

- Existing source routing, stealth retry behavior, transcript endpoints, bookmarklet behavior, and non-streaming summary endpoint remain intact.
- The client and server are updated together to consume the extra metadata in the final `done` event.
- The inactive `templates/result.html` remains out of scope unless it prevents shared-shell reuse; the active routes are `index.html` and `loading.html`.

## Verification

Add automated tests for:

- database initialization and CRUD;
- newest-first history metadata and full-record retrieval;
- rename and delete validation;
- Markdown and ZIP download contents and safe filenames;
- saving exactly one completed streaming result;
- no persistence on error, cancellation, or stealth-retry availability;
- title-generation fallback;
- updated template routes and shared-shell history controls.

Before committing the implementation, run:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile main.py fetcher.py summarizer.py storage.py
git diff --check
```

## Documentation changes

Update `README.md` with saved-history behavior, the SQLite data location, backup expectations, and the `docker-compose-example.yml` bind mount. Update `AGENTS.md` with the new persistence module, UI layout, data lifecycle, and required verification command that includes `storage.py`.
