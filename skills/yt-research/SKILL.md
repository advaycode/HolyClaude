---
name: yt-research
description: YouTube research skill powered by yt-dlp. Scrapes YouTube search results for video metadata (title, views, author, duration, URL). Use when asked to "find trending videos on X", "search YouTube for Y", "get the top N videos about Z", or as a research pipeline step before sending results to NotebookLM. IMPORTANT: If the user says to research a topic without specifying one, ask what topic they want first.
---

# yt-research

YouTube metadata scraper using yt-dlp. No API key required.

**Script location:** `~/tools/yt-research/yt_research.py`

## Trigger Phrases

- "find trending videos on [topic]"
- "search YouTube for [topic]"
- "get the top N videos about [topic]"
- "use the yt-research skill"
- Whenever a research pipeline starts with YouTube

## IMPORTANT: Always Ask for Topic First

If the user gives the research command without specifying a topic, **always ask**:

> "What topic would you like me to research on YouTube?"

Never proceed with a generic or guessed query.

## Usage

```bash
python ~/tools/yt-research/yt_research.py "QUERY" -n COUNT -f FORMAT
```

### Arguments

| Arg | Default | Description |
|-----|---------|-------------|
| `query` | required | YouTube search query |
| `-n`, `--max-results` | 25 | Number of results to fetch |
| `-f`, `--format` | `json` | Output format: `json`, `table`, `urls` |

### Examples

```bash
# Get top 25 results as JSON (default, best for pipeline)
python ~/tools/yt-research/yt_research.py "machine learning 2025" -n 25

# Human-readable table
python ~/tools/yt-research/yt_research.py "AI tutorials" -n 10 -f table

# Just URLs (for quick NotebookLM pipeline)
python ~/tools/yt-research/yt_research.py "deep learning" -n 15 -f urls
```

## Output Fields (JSON)

Each result contains:
- `rank` — position in results (1-based)
- `title` — video title
- `author` — channel/uploader name
- `duration` — formatted as `M:SS` or `H:MM:SS`
- `views` — formatted with commas (e.g., `1,234,567`)
- `view_count_raw` — integer, useful for sorting
- `url` — full YouTube URL (`https://www.youtube.com/watch?v=...`)
- `video_id` — YouTube video ID
- `upload_date` — YYYYMMDD string
- `description` — first 200 chars of description

## Pipeline Workflow (with NotebookLM)

1. Run yt-research to get video URLs as JSON
2. Extract the `url` field from each result
3. Pass URLs to the `notebooklm` skill via `pipeline` command
4. Request analysis and/or artifact generation

```bash
# Step 1: Get URLs
python ~/tools/yt-research/yt_research.py "AI agents 2025" -n 25 -f urls > /tmp/urls.txt

# Step 2: Create a JSON array of URLs for the pipeline
python ~/tools/yt-research/yt_research.py "AI agents 2025" -n 25 | python -c "
import json, sys
data = json.load(sys.stdin)
urls = [r['url'] for r in data]
with open('/tmp/yt_urls.json', 'w') as f:
    json.dump(urls, f)
print(f'Saved {len(urls)} URLs')
"
```

## Notes

- No YouTube API key required — uses yt-dlp's scraping
- Rate limits: avoid requesting >50 results in rapid succession
- "Trending" = top search results by YouTube's ranking algorithm
- For truly trending videos, add "trending 2025" or similar to your query
