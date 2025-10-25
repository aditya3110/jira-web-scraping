from typing import Any, Dict, Generator, List, Tuple

from .jira_client import JiraClient
from .checkpoint import get_project_state, load_state, save_state, update_project_state


class JiraScraper:
    def __init__(self, client: JiraClient, state_path: str) -> None:
        self.client = client
        self.state_path = state_path
        self.state = load_state(state_path)

    def _persist(self) -> None:
        save_state(self.state_path, self.state)

    def iter_project_issues(
        self,
        project_key: str,
        *,
        page_size: int = 50,
    ) -> Generator[Tuple[Dict[str, Any], List[Dict[str, Any]]], None, None]:
        project_state = get_project_state(self.state, project_key)
        start_at: int = int(project_state.get("start_at", 0))

        while True:
            jql = f"project = {project_key} ORDER BY updated ASC, created ASC"
            search = self.client.search_issues(
                jql=jql,
                start_at=start_at,
                max_results=page_size,
                fields=(
                    "summary,description,labels,created,updated,"
                    "priority,status,issuetype,reporter,assignee,project"
                ),
            )

            total = int(search.get("total", 0))
            issues: List[Dict[str, Any]] = search.get("issues") or []

            if not issues:
                # Mark done for this project
                update_project_state(self.state, project_key, start_at=total, done=True)
                self._persist()
                break

            # For each issue fetch all comments (paginated)
            for issue in issues:
                issue_key = issue.get("key")
                comments: List[Dict[str, Any]] = []
                c_start = 0
                while True:
                    cs = self.client.get_issue_comments(issue_key, start_at=c_start, max_results=100)
                    comment_values = cs.get("comments") or []
                    comments.extend(comment_values)
                    c_start += len(comment_values)
                    if c_start >= int(cs.get("total", 0)):
                        break

                yield issue, comments

            # Advance pagination checkpoint and persist
            start_at += len(issues)
            update_project_state(self.state, project_key, start_at=start_at, done=False)
            self._persist()


