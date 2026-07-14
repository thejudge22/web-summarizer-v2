# Web Summarizer

A modern web application that uses AI to summarize webpages and YouTube videos. Built with FastAPI and OpenAI, featuring a clean web interface with real-time streaming responses.

![Web Summarizer](https://img.shields.io/badge/Web-Summarizer-blue)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Features

- **Webpage Summarization**: Extract and summarize content from any webpage
- **YouTube Video Summaries**: Get detailed summaries of YouTube video transcripts
- **Real-time Streaming**: Watch the summary generate in real-time
- **Completed Summary Saving**: Finished summaries are saved with an AI-generated title; a fallback title is used if title generation is unavailable
- **Summary History API**: List, rename, delete, and export saved summaries individually or as a ZIP archive
- **Markdown Export**: Download summaries as Markdown files
- **Bookmarklet**: Quick access bookmarklet for any page
- **RESTful API**: Full API access for integration
- **Modern UI**: Clean, responsive interface built with Tailwind CSS

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- OpenAI API compatible service and API key.

### Environment Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd web-summarizer
```

2. Copy the example environment file:
```bash
cp .env.example .env
```

3. Add your OpenAI API key to `.env`:
```env
OPENAI_API_KEY=your_actual_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o
```

`OPENAI_API_KEY` is also used as the [NanoGPT](https://nano-gpt.com) API key
for YouTube transcripts. YouTube transcripts are retrieved through NanoGPT's
YouTube Transcription API; successful transcripts are billed by NanoGPT.

Webpage summaries use NanoGPT's Web Scraping API. Standard successful scrapes cost $0.001 per URL. If a normal scrape fails, the app can offer an explicit stealth-mode retry; stealth mode costs 5× the standard scrape rate and is never enabled automatically.

### Running with Docker

```bash
docker-compose up --build
```

The application will be available at `http://localhost:8000`

### Running Locally

```bash
pip install -r requirements.txt
python main.py
```

## Usage

### Web Interface

1. Open `http://localhost:8000` in your browser
2. Enter a URL (webpage or YouTube video)
3. Click "Summarize" and watch the AI generate your summary

After a summary completes, the stream's final `done` event includes its saved
`summary_id` and `title`. A completed summary is still available to download if
saving fails; in that case the event has `summary_id: null` and a `save_error`
message. Failed, cancelled, and disconnected streams are not saved.

Saved summaries appear in the responsive History sidebar on every home,
summary, and bookmarklet view. Select a row to reopen it without generating a
new summary. Use its Actions button to rename, download, or delete it (single
deletes require confirmation). Selection mode enables ZIP downloads or a
no-confirmation bulk delete for the selected rows.

Stored Markdown is rendered with a strict DOMPurify policy that excludes SVG,
MathML, embedded content, styles, and unsafe link protocols.

Saved summaries are also available at `/summaries/{summary_id}` and through
the history API. `GET /api/summaries` lists metadata, while `GET`, `PATCH`,
and `DELETE /api/summaries/{summary_id}` retrieve, rename, or remove a record.
Use `GET /api/summaries/{summary_id}/download` to download Markdown, or send
an `{"ids": [1, 2]}` JSON body to `POST /api/summaries/download-zip` or
`POST /api/summaries/bulk-delete` for bulk exports or deletion.

### Bookmarklet

For quick access on any page:

1. Drag the "Summarize This Page" button to your bookmarks bar
2. Click it while viewing any page to open a summary in a new tab

## Configuration

### Prompt Customization
The prompt files are located in the project root.  You can customize the prompts (youtube.md and page-summary.md) as needed. Make the changes to the prompts and rebuild the container.

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key; also the NanoGPT API key for webpage scraping and YouTube transcripts | Required |
| `OPENAI_BASE_URL` | OpenAI API base URL | `https://api.openai.com/v1` |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4o` |

## License

MIT License - feel free to use this project for personal or commercial purposes.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and feature requests, please use the GitHub issue tracker.
