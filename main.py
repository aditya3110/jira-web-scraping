import json
import os
from typing import List

from jira_scraper.jira_client import JiraClient
from jira_scraper.scraper import JiraScraper
from jira_scraper.transform import transform_issue


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def write_jsonl_record(path: str, obj: dict) -> None:
    ensure_parent_dir(path)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")



def main() -> None:

    with open("config.json", "r") as f:
        config = json.load(f)

    client = JiraClient(
        rate_limit_rps=config["rate_limit"],
        timeout_seconds=config["timeout"]
    )
    scraper = JiraScraper(
        client,
        state_path=config["state"]
    )

    for project_key in config["projects"]:
        exported = 0
        for issue, comments in scraper.iter_project_issues(
                project_key,
                page_size=config["page_size"]
        ):
            record = transform_issue(issue, comments)
            write_jsonl_record(config["out"], record)
            exported += 1
            if config["max_per_project"] is not None and exported >= config["max_per_project"]:
                break


if __name__ == "__main__":
    main()


