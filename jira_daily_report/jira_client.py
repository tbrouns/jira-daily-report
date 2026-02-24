from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

from jira_daily_report.date_utils import as_local_date
from jira_daily_report.text_extract import adf_to_text

DEFAULT_ISSUE_FIELDS = [
    "summary",
    "description",
    "comment",
    "assignee",
    "parent",
    "subtasks",
    "issuetype",
    "project",
]


@dataclass(frozen=True)
class DailyIssueSet:
    by_day_issue_seconds: dict[date, dict[str, int]]


class JiraClient:
    def __init__(self, base_url: str, email: str, api_token: str, timeout_seconds: int = 30):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(email, api_token)
        self.session.headers.update({"Accept": "application/json"})
        self.timeout_seconds = timeout_seconds

    def resolve_user(self, email: str) -> dict[str, Any]:
        # Jira Cloud user visibility can hide emails; query-based search is the broadest read path.
        users = self._get(
            "/rest/api/3/user/search",
            params={"query": email, "maxResults": 50},
            expect_list=True,
        )
        lowered = email.lower()
        for user in users:
            if str(user.get("emailAddress", "")).lower() == lowered:
                return user
        if len(users) == 1:
            return users[0]
        for user in users:
            display = str(user.get("displayName", "")).lower()
            if lowered in display or lowered.split("@")[0] in display:
                return user
        raise ValueError(f"Could not resolve Jira user for email: {email}")

    def get_issue_keys_with_worklogs_for_month(
        self,
        month_start: date,
        month_end: date,
        target_account_id: str,
        target_email: str,
        timezone: str,
    ) -> DailyIssueSet:
        jql = f'worklogDate >= "{month_start.isoformat()}" AND worklogDate <= "{month_end.isoformat()}"'

        issues = self._search_issues(jql=jql, fields=["worklog"])

        by_day: dict[date, dict[str, int]] = {}
        for issue in issues:
            issue_key = issue["key"]
            for worklog in self._get_all_worklogs(issue_key):
                if not self._is_target_worklog(worklog, target_account_id, target_email):
                    continue
                local_day = as_local_date(worklog["started"], timezone)
                if month_start <= local_day <= month_end:
                    issue_seconds = int(worklog.get("timeSpentSeconds") or 0)
                    day_bucket = by_day.setdefault(local_day, {})
                    day_bucket[issue_key] = day_bucket.get(issue_key, 0) + issue_seconds

        return DailyIssueSet(by_day_issue_seconds=by_day)

    def get_issue_bundle(self, issue_keys: set[str], epic_field_id: str | None) -> dict[str, dict[str, Any]]:
        cache: dict[str, dict[str, Any]] = {}

        for key in sorted(issue_keys):
            issue = self._get_issue(key)
            cache[key] = issue

        additional_keys: set[str] = set()
        for issue in cache.values():
            fields = issue.get("fields", {})

            parent = fields.get("parent")
            if isinstance(parent, dict) and parent.get("key"):
                additional_keys.add(parent["key"])

            for subtask in fields.get("subtasks") or []:
                if isinstance(subtask, dict) and subtask.get("key"):
                    additional_keys.add(subtask["key"])

            epic_key = self._extract_epic_key(fields, epic_field_id)
            if epic_key:
                additional_keys.add(epic_key)

        for key in sorted(additional_keys - cache.keys()):
            cache[key] = self._get_issue(key)

        return cache

    def detect_epic_link_field_id(self) -> str | None:
        fields = self._get("/rest/api/3/field", expect_list=True)
        for field in fields:
            if str(field.get("name", "")).strip().lower() == "epic link":
                return field.get("id")
        return None

    def render_issue_text(self, issue: dict[str, Any]) -> str:
        key = issue.get("key", "UNKNOWN")
        fields = issue.get("fields", {})

        summary = fields.get("summary", "")
        description = adf_to_text(fields.get("description"))
        comments = fields.get("comment", {}).get("comments", [])
        comment_texts = [adf_to_text(comment.get("body")) for comment in comments]

        parent = fields.get("parent")
        parent_key = parent.get("key") if isinstance(parent, dict) else None

        subtasks = fields.get("subtasks") or []
        subtask_keys = [task.get("key") for task in subtasks if isinstance(task, dict) and task.get("key")]

        lines = [f"Issue: {key}", f"Title: {summary}"]

        if parent_key:
            lines.append(f"Direct Parent: {parent_key}")
        if subtask_keys:
            lines.append(f"Direct Subtasks: {', '.join(subtask_keys)}")

        if description:
            lines.extend(["Description:", description])

        if any(comment_texts):
            lines.append("Comments:")
            for idx, text in enumerate(comment_texts, start=1):
                if text:
                    lines.append(f"{idx}. {text}")

        return "\n".join(lines).strip()

    def _extract_epic_key(self, fields: dict[str, Any], epic_field_id: str | None) -> str | None:
        parent = fields.get("parent")
        if isinstance(parent, dict):
            parent_type = str(parent.get("fields", {}).get("issuetype", {}).get("name", "")).lower()
            if parent_type == "epic" and parent.get("key"):
                return parent["key"]

        if epic_field_id:
            value = fields.get(epic_field_id)
            if isinstance(value, str) and value.strip():
                return value.strip()

        epic_candidate = fields.get("epic")
        if isinstance(epic_candidate, dict) and epic_candidate.get("key"):
            return epic_candidate["key"]

        return None

    def _is_target_worklog(self, worklog: dict[str, Any], account_id: str, email: str) -> bool:
        author = worklog.get("author", {})
        if author.get("accountId") == account_id:
            return True
        return str(author.get("emailAddress", "")).lower() == email.lower()

    def _search_issues(self, jql: str, fields: list[str]) -> list[dict[str, Any]]:
        max_results = 100
        all_issues: list[dict[str, Any]] = []
        next_page_token: str | None = None
        start_at = 0

        while True:
            payload = {
                "jql": jql,
                "fields": fields,
                "maxResults": max_results,
            }
            if next_page_token:
                payload["nextPageToken"] = next_page_token
            else:
                # Backward-compatible pagination parameter if nextPageToken is not used by the tenant.
                payload["startAt"] = start_at

            data = self._post("/rest/api/3/search/jql", json=payload)
            issues = data.get("issues", [])
            all_issues.extend(issues)

            next_page_token = data.get("nextPageToken")
            if isinstance(next_page_token, str) and next_page_token:
                if not issues:
                    break
                continue

            total = data.get("total")
            if isinstance(total, int):
                start_at += len(issues)
                if start_at < total and issues:
                    continue
            break

        return all_issues

    def _get_issue(self, issue_key: str) -> dict[str, Any]:
        return self._get(
            f"/rest/api/3/issue/{issue_key}",
            params={"fields": ",".join(DEFAULT_ISSUE_FIELDS)},
        )

    def _get_all_worklogs(self, issue_key: str) -> list[dict[str, Any]]:
        start_at = 0
        max_results = 100
        logs: list[dict[str, Any]] = []

        while True:
            data = self._get(
                f"/rest/api/3/issue/{issue_key}/worklog",
                params={"startAt": start_at, "maxResults": max_results},
            )
            values = data.get("worklogs", [])
            logs.extend(values)

            total = int(data.get("total", 0))
            start_at += len(values)
            if start_at >= total or not values:
                break

        return logs

    def _get(self, path: str, params: dict[str, Any] | None = None, expect_list: bool = False):
        url = f"{self.base_url}{path}"
        response = self.session.get(url, params=params, timeout=self.timeout_seconds)
        return self._decode_response(response, expect_list=expect_list)

    def _post(self, path: str, json: dict[str, Any]):
        url = f"{self.base_url}{path}"
        response = self.session.post(url, json=json, timeout=self.timeout_seconds)
        return self._decode_response(response)

    @staticmethod
    def _decode_response(response: requests.Response, expect_list: bool = False):
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = ""
            try:
                detail = response.text
            except Exception:
                detail = "<no response body>"
            raise RuntimeError(
                f"Jira API request failed ({response.status_code} {response.reason}): {detail}"
            ) from exc

        data = response.json()
        if expect_list and not isinstance(data, list):
            raise RuntimeError("Expected Jira API to return a list")
        return data
