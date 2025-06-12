import os
import json
import time
from urllib.parse import urlparse, parse_qs

import requests
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi
import openai

PROCESSED_FILE = "processed.json"
YOUTUBE_API = "https://www.googleapis.com/youtube/v3"


def load_processed():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE) as f:
            return set(json.load(f))
    return set()


def save_processed(processed):
    with open(PROCESSED_FILE, "w") as f:
        json.dump(sorted(list(processed)), f, indent=2)


def parse_url(url: str):
    """Return (id, is_playlist)."""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if 'list' in qs and 'playlist' in parsed.path:
        return qs['list'][0], True
    if 'list' in qs and 'watch' in parsed.path and 'v' not in qs:
        # playlist URL without v parameter
        return qs['list'][0], True
    if 'watch' in parsed.path and 'v' in qs:
        return qs['v'][0], False
    raise ValueError("Could not determine if URL is video or playlist")


def playlist_videos(playlist_id: str, api_key: str):
    token = None
    videos = []
    while True:
        params = {
            "part": "contentDetails",
            "playlistId": playlist_id,
            "maxResults": 50,
            "pageToken": token,
            "key": api_key,
        }
        resp = requests.get(f"{YOUTUBE_API}/playlistItems", params=params)
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("items", []):
            videos.append(item["contentDetails"]["videoId"])
        token = data.get("nextPageToken")
        if not token:
            break
    return videos


def get_transcript(video_id: str):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        text = " ".join(t["text"] for t in transcript)
        return text
    except Exception as e:
        print(f"Could not fetch transcript for {video_id}: {e}")
        return None


def summarize(text: str, instructions: str):
    prompt = instructions + "\n\nTranscript:\n" + text
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
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
    page = resp.json()
    return page.get("id")


def process_video(video_id: str, instructions: str, api_key: str, notion_token: str, notion_parent: str):
    transcript = get_transcript(video_id)
    if not transcript:
        return
    print(f"Summarizing {video_id}...")
    summary = summarize(transcript, instructions)
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    title = youtube_url
    page_id = create_notion_page(title, summary, notion_token, notion_parent)
    print(f"Created Notion page {page_id} for {video_id}")


def main():
    load_dotenv()
    openai.api_key = os.environ.get("OPENAI_API_KEY")
    yt_key = os.environ.get("YOUTUBE_API_KEY")
    notion_token = os.environ.get("NOTION_API_KEY")
    notion_parent = os.environ.get("NOTION_PARENT_ID")
    if not all([openai.api_key, yt_key, notion_token, notion_parent]):
        print("Missing environment variables. Check .env file.")
        return
    processed = load_processed()

    url = input("Enter YouTube video or playlist URL: ").strip()
    instructions = input("Enter summarization instructions: ").strip()
    try:
        _id, is_playlist = parse_url(url)
    except ValueError as e:
        print(e)
        return

    if is_playlist:
        videos = playlist_videos(_id, yt_key)
    else:
        videos = [_id]

    for vid in videos:
        if vid in processed:
            print(f"Skipping {vid}, already processed")
            continue
        process_video(vid, instructions, yt_key, notion_token, notion_parent)
        processed.add(vid)
        save_processed(processed)


if __name__ == "__main__":
    main()
