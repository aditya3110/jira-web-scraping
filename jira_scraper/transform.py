from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup


def _to_plain_text(value: Optional[str]) -> str:
    if not value:
        return ""
    text = value.strip()
    # If it looks like HTML, strip tags; otherwise return as-is
    if "<" in text and ">" in text:
        try:
            soup = BeautifulSoup(text, "html.parser")
            return soup.get_text("\n").strip()
        except Exception:
            return text
    return text


def transform_issue(issue: Dict[str, Any], comments: List[Dict[str, Any]]) -> Dict[str, Any]:
    fields = issue.get("fields", {}) or {}
    issue_type = (fields.get("issuetype") or {}).get("name")
    status = (fields.get("status") or {}).get("name")
    priority = (fields.get("priority") or {}).get("name")
    assignee = (fields.get("assignee") or {}).get("displayName")
    reporter = (fields.get("reporter") or {}).get("displayName")
    labels = fields.get("labels") or []

    summary = fields.get("summary") or ""
    description_text = _to_plain_text(fields.get("description"))
    comment_bodies = [_to_plain_text((c or {}).get("body")) for c in comments or []]

    # Base record
    record: Dict[str, Any] = {
        "id": issue.get("id"),
        "key": issue.get("key"),
        "project_key": (fields.get("project") or {}).get("key"),
        "title": summary,
        "description": description_text,
        "comments": [c for c in comment_bodies if c],
        "status": status,
        "type": issue_type,
        "priority": priority,
        "assignee": assignee,
        "reporter": reporter,
        "labels": labels,
        "created": fields.get("created"),
        "updated": fields.get("updated"),
        "url": f"https://issues.apache.org/jira/browse/{issue.get('key')}",
    }

    # Derived tasks for LLM training
    context_text = "\n\n".join(
        [p for p in [summary, description_text] if p] +
        (["\n\n".join(comment_bodies)] if comment_bodies else [])
    ).strip()

    tasks: List[Dict[str, Any]] = []

    if context_text:
        tasks.append(
            {
                "type": "summarization",
                "instruction": "Summarize the following Jira issue and discussion in 2-3 sentences.",
                "input": context_text,
                "target": summary or (description_text[:200] + "...") if description_text else "",
            }
        )

    if issue_type:
        tasks.append(
            {
                "type": "classification",
                "instruction": "Classify the Jira issue type (e.g., Bug, Improvement, Task).",
                "input": context_text or summary,
                "target": issue_type,
            }
        )

    if context_text:
        tasks.append(
            {
                "type": "qna",
                "instruction": "Answer the question based on the issue content.",
                "input": {
                    "question": "What is this issue about?",
                    "context": context_text,
                },
                "target": summary,
            }
        )

    record["tasks"] = tasks
    return record


