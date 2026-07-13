import os
import re
import time
from typing import Optional, Tuple

import requests
import trafilatura


NANOGPT_YOUTUBE_TRANSCRIBE_URL = "https://nano-gpt.com/api/youtube-transcribe"
NANOGPT_REQUEST_TIMEOUT_SECONDS = 30
NANOGPT_RATE_LIMIT_DELAYS_SECONDS = (5, 10)


def is_youtube_url(url: str) -> bool:
    pattern = r'(youtube\.com|youtu\.be)'
    return bool(re.search(pattern, url))


def extract_video_id(url: str) -> Optional[str]:
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/watch\?.*v=([^&\n?#]+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def clean_youtube_url(url: str) -> str:
    """
    Strips extra query parameters from a YouTube URL, returning a clean version
    typically in the format https://www.youtube.com/watch?v={video_id}.
    If it's not a YouTube URL or ID extraction fails, returns the original URL.
    """
    if not is_youtube_url(url):
        return url
    
    video_id = extract_video_id(url)
    if not video_id:
        return url
        
    return f"https://www.youtube.com/watch?v={video_id}"


def fetch_youtube_transcript(url: str) -> Tuple[str, str]:
    if not extract_video_id(url):
        raise ValueError("Could not extract YouTube video ID from URL")
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set in environment variables")

    for attempt in range(3):
        try:
            response = requests.post(
                NANOGPT_YOUTUBE_TRANSCRIBE_URL,
                json={"urls": [clean_youtube_url(url)]},
                headers={"Content-Type": "application/json", "x-api-key": api_key},
                timeout=NANOGPT_REQUEST_TIMEOUT_SECONDS,
            )
        except requests.RequestException as error:
            raise ValueError(f"Error contacting NanoGPT transcription service: {error}") from error
        if response.status_code == 429:
            if attempt == 2:
                raise ValueError("NanoGPT transcription rate limit exceeded after 3 attempts")
            time.sleep(NANOGPT_RATE_LIMIT_DELAYS_SECONDS[attempt])
            continue
        if not response.ok:
            try:
                message = response.json().get("error", response.text)
            except ValueError:
                message = response.text
            raise ValueError(f"NanoGPT transcription request failed: {message}")
        try:
            result = response.json()["transcripts"][0]
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise ValueError("NanoGPT returned an invalid transcription response") from error
        if not isinstance(result, dict):
            raise ValueError("NanoGPT returned an invalid transcription response")
        if not result.get("success"):
            raise ValueError(result.get("error") or "No transcript found for this video")
        transcript = result.get("transcript")
        if not isinstance(transcript, str) or not transcript.strip():
            raise ValueError("NanoGPT returned an empty transcript")
        return transcript, "YouTube"
    raise AssertionError("Unreachable retry state")


def fetch_webpage_content(url: str) -> Tuple[str, str]:
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise ValueError("Could not fetch the webpage")
    
    content = trafilatura.extract(downloaded)
    if not content:
        raise ValueError("Could not extract content from the webpage")
    
    return content, "Webpage"


def fetch_content(url: str) -> Tuple[str, str]:
    if is_youtube_url(url):
        return fetch_youtube_transcript(url)
    else:
        return fetch_webpage_content(url)
