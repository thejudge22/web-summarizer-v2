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
| `OPENAI_API_KEY` | OpenAI API key | Required |
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
