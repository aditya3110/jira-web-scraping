## Apache Jira Web Scraping → JSONL (LLM-ready)

This project scrapes public issues from Apache Jira and converts them into JSONL suitable for LLM training. It handles pagination, retries, 429/5xx backoff, resumable checkpointing, and transforms HTML descriptions/comments into plain text with derived tasks.

### Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Usage

```bash
  python main.py
```
###  Config.py
```json
{
  "projects": ["ABDERA", "ACCUMULO", "AMQNET"],
  "out": "data/apache_jira.jsonl",
  "state": "data/state.json",
  "page_size": 50,
  "rate_limit": 3.0,
  "timeout": 20.0,
  "max_per_project": null
}
```
Currently above are the configuration, you can change the values accordingly
### Output Schema

Each line is a JSON object including metadata, plain-text content, and derived tasks. Example shape:

```json
{
  "id": "123456",
  "key": "SPARK-12345",
  "project_key": "SPARK",
  "title": "Fix null pointer in executor",
  "description": "...plain text...",
  "comments": ["...", "..."],
  "status": "Resolved",
  "type": "Bug",
  "priority": "Major",
  "assignee": "Alice",
  "reporter": "Bob",
  "labels": ["performance"],
  "created": "2021-01-01T00:00:00.000+0000",
  "updated": "2021-01-02T00:00:00.000+0000",
  "url": "https://issues.apache.org/jira/browse/SPARK-12345",
  "tasks": [
    {"type": "summarization", "instruction": "...", "input": "...", "target": "..."},
    {"type": "classification", "instruction": "...", "input": "...", "target": "Bug"},
    {"type": "qna", "instruction": "...", "input": {"question": "...", "context": "..."}, "target": "..."}
  ]
}
```

### Notes

- Uses only public data from `https://issues.apache.org/jira` and respects rate limits with exponential backoff and jitter.
- Checkpoints after each page to allow interruption and later resume without re-scraping.
- HTML fields are converted to plain text using BeautifulSoup; malformed HTML is handled gracefully.


