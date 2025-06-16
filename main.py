import os
import json
from urllib.parse import urlparse, parse_qs
from pathlib import Path

import requests
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
import openai

PROCESSED_FILE = "processed.json"
YOUTUBE_API = "https://www.googleapis.com/youtube/v3"

INSTRUCTIONS = (
    "Users will give you a podcast transcript or other long-form content. Read it and create an extensive yet relevant summary, around 1,000 words in length.\n\n"
    "When writing a summary, follow this approach:\n\n"
    "1. Start with a section on the 'So what': for the user, based on what you know about them. Why should they care about this content, if at all, and how to best apply it specifically in the user's life.\n"
    "2. Provide a section about Important ideas that are one or many of the following: memorable, surprising, counterintuitive, contrarian, insightful, applicable. Try to stay away from generic or useless ideas as much as possible.\n"
    "3. List all relevant resources mentioned such as books, research papers, movies, songs, or anything else that might be interesting for the user to further explore.\n"
    "4. Include the source URL in hyperlink at the end of your summary."
)

def load_processed():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE) as f:
            return set(json.load(f))
    return set()

def save_processed(processed):
    with open(PROCESSED_FILE, "w") as f:
        json.dump(sorted(list(processed)), f, indent=2)

def parse_video_url(url: str):
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if 'v' in qs:
        return qs['v'][0]
    if parsed.netloc == "youtu.be":
        return parsed.path.strip('/')
    raise ValueError("Could not extract video ID from URL")

def get_video_title(video_id: str, api_key: str):
    url = f"{YOUTUBE_API}/videos"
    params = {
        "part": "snippet",
        "id": video_id,
        "key": api_key
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    items = response.json().get("items")
    if not items:
        return f"YouTube Video {video_id}"
    return items[0]["snippet"]["title"]

def get_transcript(video_id: str):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join(t["text"] for t in transcript)
    except Exception as e:
        print(f"Could not fetch transcript for {video_id}: {e}")
        return None

def summarize(text: str, instructions: str):
    prompt = instructions + "\n\nTranscript:\n" + text
    resp = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return resp["choices"][0]["message"]["content"].strip()

def create_notion_page(title: str, summary: str, notion_token: str, parent_id: str):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    data = {
        "parent": {"page_id": parent_id},
        "properties": {
            "title": {
                "title": [{"text": {"content": title}}]
            }
        },
        "children": [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "text": [
                        {"type": "text", "text": {"content": summary}}
                    ]
                }
            }
        ]
    }
    resp = requests.post(url, headers=headers, json=data)
    resp.raise_for_status()
    return resp.json().get("id")

def save_markdown(title: str, summary: str):
    filename = Path("summaries") / (title.replace(" ", "_").replace("/", "-") + ".md")
    filename.parent.mkdir(exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n{summary}\n")
    print(f"📝 Saved local markdown: {filename}")

def process_video(video_id: str, video_url: str, api_key: str, notion_token: str, notion_parent: str):
    transcript = get_transcript(video_id)
    if not transcript:
        return
    title = get_video_title(video_id, api_key)
    print(f"Summarizing: {title} ({video_id})...")
    summary = summarize(transcript, INSTRUCTIONS)
    summary += f"\n\n[Source]({video_url})"
    notion_page_id = create_notion_page(title, summary, notion_token, notion_parent)
    print(f"✅ Created Notion page: {notion_page_id}")
    save_markdown(title, summary)

def main():
    load_dotenv()
    openai.api_key = os.getenv("OPENAI_API_KEY")
    yt_key = os.getenv("YOUTUBE_API_KEY")
    notion_token = os.getenv("NOTION_API_KEY")
    notion_parent = os.getenv("NOTION_PARENT_ID")

    if not all([openai.api_key, yt_key, notion_token, notion_parent]):
        print("❌ Missing environment variables. Check your .env file.")
        return

    processed = load_processed()
    url = input("Paste YouTube video URL: ").strip()

    try:
        video_id = parse_video_url(url)
    except ValueError as e:
        print(e)
        return

    if video_id in processed:
        print(f"⏭ Skipping {video_id}, already processed.")
        return

    process_video(video_id, url, yt_key, notion_token, notion_parent)
    processed.add(video_id)
    save_processed(processed)

if __name__ == "__main__":
    main()
