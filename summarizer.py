import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def get_system_prompt(source_type: str) -> str:
    if source_type == "YouTube":
        with open("youtube.md", "r") as f:
            return f.read()
    else:
        with open("page-summary.md", "r") as f:
            return f.read()


def summarize_content(content: str, source_type: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set in environment variables")
    
    client = OpenAI(api_key=api_key, base_url=base_url)
    system_prompt = get_system_prompt(source_type)
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ],
        temperature=0.7
    )
    
    return response.choices[0].message.content