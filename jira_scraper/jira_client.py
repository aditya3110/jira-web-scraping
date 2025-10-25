import time
import random
from typing import Any, Dict, Optional

import requests


class JiraClient:
    """
    Minimal Jira REST client for Apache Jira (Server/DC API v2).

    Handles retries, simple rate limiting, and HTTP 429/5xx backoff.
    """

    def __init__(
        self,
        base_url: str = "https://issues.apache.org/jira",
        *,
        rate_limit_rps: float = 3.0,
        timeout_seconds: float = 20.0,
        max_retries: int = 5,
        backoff_base_seconds: float = 1.0,
        user_agent: str = "jira-web-scraping/1.0 (+LLM dataset builder)",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": user_agent,
            }
        )
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds

        # Simple rate limiter: enforce minimum interval between requests
        # If rate_limit_rps is 3, then min_interval is ~0.333s
        self.min_interval = 1.0 / max(rate_limit_rps, 0.1)
        self._last_request_time = 0.0

    def _respect_rate_limit(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        last_error: Optional[BaseException] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                self._respect_rate_limit()
                response = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    timeout=self.timeout_seconds,
                )
                self._last_request_time = time.monotonic()

                # Handle rate limiting and transient server errors
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after is not None:
                        try:
                            sleep_seconds = float(retry_after)
                        except ValueError:
                            sleep_seconds = self._compute_backoff(attempt)
                    else:
                        sleep_seconds = self._compute_backoff(attempt)
                    time.sleep(sleep_seconds)
                    continue

                if 500 <= response.status_code < 600:
                    time.sleep(self._compute_backoff(attempt))
                    continue

                response.raise_for_status()
                json_body = response.json()
                return json_body if isinstance(json_body, dict) else json_body

            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = exc
                time.sleep(self._compute_backoff(attempt))
            except requests.RequestException as exc:
                # Non-retryable HTTP error
                raise exc

        # Retries exhausted
        if last_error is not None:
            raise last_error
        raise RuntimeError("Request failed without specific exception")

    def _compute_backoff(self, attempt: int) -> float:
        # Exponential backoff with jitter
        base = self.backoff_base_seconds * (2 ** (attempt - 1))
        jitter = random.uniform(0.5, 1.5)
        # Cap to 60s to avoid excessive delays
        return min(base * jitter, 60.0)

    # Public API
    def search_issues(
        self,
        *,
        jql: str,
        start_at: int = 0,
        max_results: int = 50,
        fields: Optional[str] = None,
        expand: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
        }
        if fields:
            params["fields"] = fields
        if expand:
            params["expand"] = expand
        return self._request("GET", "/rest/api/2/search", params=params)

    def get_issue_comments(
        self,
        issue_key: str,
        *,
        start_at: int = 0,
        max_results: int = 100,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "startAt": start_at,
            "maxResults": max_results,
        }
        return self._request("GET", f"/rest/api/2/issue/{issue_key}/comment", params=params)


