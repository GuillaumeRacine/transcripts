# Transcript Summarizer

A simple command-line tool that retrieves YouTube transcripts, summarizes them using an LLM, stores the results in Notion and saves a local markdown copy.

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

Run the script and follow the prompt:

```bash
python main.py
```

When prompted, paste a YouTube video URL. The application fetches the transcript, generates a long summary using GPT-4 according to the built‑in instructions, creates a new Notion page under the configured parent and stores the same summary locally in the `summaries/` folder. Previously processed videos are recorded in `processed.json` to avoid duplicates.
