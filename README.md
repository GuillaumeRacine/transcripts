# Transcript Summarizer

A simple command-line tool that retrieves YouTube transcripts, summarizes them using an LLM, and stores the results in Notion.

## Setup

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Create a `.env` file with the following variables:

```
OPENAI_API_KEY=your-openai-key
YOUTUBE_API_KEY=your-youtube-data-api-key
NOTION_API_KEY=your-notion-token
NOTION_PARENT_ID=parent-page-id
```

## Usage

Run the script and follow the prompts:

```bash
python main.py
```

Enter a YouTube video or playlist URL when prompted and provide instructions for the LLM to generate your summary. A new Notion page will be created for each processed video. Previously processed videos are recorded in `processed.json` to avoid duplicates.
