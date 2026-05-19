---
name: notebooklm
description: NotebookLM automation skill powered by notebooklm-py (Teng Lin's unofficial API). Creates notebooks, uploads YouTube URLs and other sources, asks analysis questions, and generates deliverables (infographic, slides, flashcards, quiz, audio, video, mindmap, report, data table). Use when asked to "send to NotebookLM", "create a NotebookLM notebook", "generate an infographic/slides/flashcards from these videos", or as the second step in a yt-research → NotebookLM pipeline.
---

# notebooklm

NotebookLM automation via the unofficial notebooklm-py library.

**Script location:** `~/tools/notebooklm/notebooklm_skill.py`

## Authentication (Required First Time)

Before using this skill, the user must authenticate once:

```bash
notebooklm login
```

This opens a browser window for Google account login. Credentials are stored locally and reused in future sessions.

**Remind the user:** Open a separate terminal window and run `notebooklm login` if they haven't already.

## Commands

### 1. List Notebooks
```bash
python ~/tools/notebooklm/notebooklm_skill.py list
```

### 2. Create Notebook
```bash
python ~/tools/notebooklm/notebooklm_skill.py create "My Research Notebook"
```
Returns: `{"notebook_id": "...", "name": "..."}`

### 3. Add Sources
```bash
python ~/tools/notebooklm/notebooklm_skill.py add-sources NOTEBOOK_ID URL1 URL2 URL3...
```

### 4. Ask a Question (Analysis)
```bash
python ~/tools/notebooklm/notebooklm_skill.py ask NOTEBOOK_ID "What are the top findings and trends?"
```

### 5. Generate Artifact
```bash
python ~/tools/notebooklm/notebooklm_skill.py artifact NOTEBOOK_ID TYPE --instructions "STYLE INSTRUCTIONS"
```

**Artifact types:**
| Type | Description |
|------|-------------|
| `infographic` | Visual infographic (multiple orientations) |
| `slides` | Slide deck (exportable as PDF/PPTX) |
| `flashcards` | Study flashcards |
| `quiz` | Quiz with configurable difficulty |
| `audio` | Audio overview / deep dive |
| `video` | Video overview |
| `mindmap` | Mind map (JSON) |
| `report` | Study guide, blog post, or briefing |
| `table` | Data table (exportable as CSV) |

### 6. Full Pipeline (One-Shot)
```bash
python ~/tools/notebooklm/notebooklm_skill.py pipeline "Notebook Name" \
  --sources-file /tmp/yt_urls.json \
  --question "What are the top trends and key findings?" \
  --artifact infographic \
  --instructions "Handwritten chalkboard style, dark background"
```

Or with inline sources:
```bash
python ~/tools/notebooklm/notebooklm_skill.py pipeline "AI Research" \
  --sources "https://youtube.com/watch?v=X" "https://youtube.com/watch?v=Y" \
  --question "Summarize the main themes" \
  --artifact slides
```

## Full yt-research → NotebookLM Pipeline

```bash
# Step 1: Research YouTube
python ~/tools/yt-research/yt_research.py "YOUR TOPIC trending 2025" -n 25 | python -c "
import json, sys
data = json.load(sys.stdin)
urls = [r['url'] for r in data]
with open('/tmp/yt_urls.json', 'w') as f:
    json.dump(urls, f)
print(f'Saved {len(urls)} URLs to /tmp/yt_urls.json')
"

# Step 2: Run full NotebookLM pipeline
python ~/tools/notebooklm/notebooklm_skill.py pipeline "YouTube Research: YOUR TOPIC" \
  --sources-file /tmp/yt_urls.json \
  --question "What are the top findings, trends, and key insights from these videos?" \
  --artifact infographic \
  --instructions "STYLE INSTRUCTIONS HERE"
```

## Infographic Style Instructions Examples

- `"Handwritten chalkboard style, dark background, white chalk text, diagram-heavy"`
- `"Clean minimalist infographic, pastel colors, modern sans-serif font"`
- `"Bold data visualization, neon colors on dark background"`
- `"Academic research poster style, formal layout, muted tones"`

## Notes

- **Unofficial API**: Uses undocumented Google APIs — may break with NotebookLM updates
- **Source limit**: NotebookLM supports up to 50 sources per notebook
- **Auth**: Session stored locally after `notebooklm login`; re-login if session expires
- **Async**: All operations are async internally; the CLI handles this automatically
