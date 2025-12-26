import re
from typing import Tuple, Optional
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import trafilatura


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


def fetch_youtube_transcript(url: str) -> Tuple[str, str]:
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError("Could not extract YouTube video ID from URL")
    
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([item['text'] for item in transcript])
        return transcript_text, "YouTube"
    except TranscriptsDisabled:
        raise ValueError("Transcripts are disabled for this video")
    except NoTranscriptFound:
        raise ValueError("No transcript found for this video")
    except Exception as e:
        raise ValueError(f"Error fetching transcript: {str(e)}")


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