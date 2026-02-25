from __future__ import annotations

from datetime import date
from typing import Any

from jira_daily_report.jira_client import JiraClient


def build_daily_prompt(
    day: date,
    issue_seconds: dict[str, int],
    issues_by_key: dict[str, dict[str, Any]],
    jira_client: JiraClient,
    epic_field_id: str | None,
    target_account_id: str,
    target_email: str,
) -> str:
    issue_sections: list[str] = []

    total_seconds = sum(issue_seconds.values())

    for key in sorted(issue_seconds):
        issue = issues_by_key[key]
        hours = issue_seconds[key] / 3600
        sections = [f"Time Logged On This Day: {hours:.2f}h"]

        fields = issue.get("fields", {})
        epic_summary = _extract_epic_summary(fields=fields, issues_by_key=issues_by_key, epic_field_id=epic_field_id)
        project_name = _extract_project_name(fields)
        epic_preface = _build_epic_preface(epic_summary=epic_summary, project_name=project_name)
        if epic_preface:
            sections.append(f"Epic Preface: {epic_preface}")

        if _is_issue_assigned_to_target(issue, target_account_id, target_email):
            sections.append(jira_client.render_issue_text(issue))

            parent = fields.get("parent")
            if isinstance(parent, dict) and parent.get("key"):
                parent_key = parent["key"]
                parent_issue = issues_by_key.get(parent_key)
                if parent_issue and _is_issue_assigned_to_target(parent_issue, target_account_id, target_email):
                    sections.append("Parent Context:\n" + jira_client.render_issue_text(parent_issue))

            for subtask in fields.get("subtasks") or []:
                subtask_key = subtask.get("key") if isinstance(subtask, dict) else None
                if not subtask_key:
                    continue
                subtask_issue = issues_by_key.get(subtask_key)
                if subtask_issue and _is_issue_assigned_to_target(subtask_issue, target_account_id, target_email):
                    sections.append("Subtask Context:\n" + jira_client.render_issue_text(subtask_issue))

            epic_key = _extract_epic_key(fields, epic_field_id)
            if epic_key:
                epic_issue = issues_by_key.get(epic_key)
                if epic_issue:
                    sections.append("Epic Context:\n" + jira_client.render_issue_text(epic_issue))
        else:
            sections.append(f"Issue: {key}")
            sections.append("Issue details omitted because assignee does not match target user.")

        issue_sections.append("\n\n".join(sections))

    header = [
        f"Date: {day.isoformat()}",
        f"Total Logged Time: {total_seconds / 3600:.2f}h",
        "Summarize the work completed this day based on Jira issue context.",
        "Only use issue details when the issue assignee matches the target user.",
        "Focus only on high-level completed outcomes.",
        "Group topics by unique Epic Preface and print each preface only once.",
        'Format as: "<Epic Preface>:" followed by one short high-level sentence per line.',
        'If Epic Preface is unavailable, group lines under "General:".',
        "Do not include dates or time-window markers in prefaces or topic lines.",
    ]

    return "\n\n".join(["\n".join(header)] + issue_sections)


def _extract_epic_key(fields: dict[str, Any], epic_field_id: str | None) -> str | None:
    parent = fields.get("parent")
    if isinstance(parent, dict):
        p_type = str(parent.get("fields", {}).get("issuetype", {}).get("name", "")).lower()
        if p_type == "epic" and parent.get("key"):
            return parent["key"]

    if epic_field_id:
        value = fields.get(epic_field_id)
        if isinstance(value, str) and value.strip():
            return value.strip()

    epic_candidate = fields.get("epic")
    if isinstance(epic_candidate, dict) and epic_candidate.get("key"):
        return epic_candidate["key"]

    return None


def _extract_epic_summary(
    *,
    fields: dict[str, Any],
    issues_by_key: dict[str, dict[str, Any]],
    epic_field_id: str | None,
) -> str | None:
    epic_key = _extract_epic_key(fields, epic_field_id)
    if not epic_key:
        return None
    epic_issue = issues_by_key.get(epic_key)
    if not isinstance(epic_issue, dict):
        return None
    epic_fields = epic_issue.get("fields", {})
    epic_summary = str(epic_fields.get("summary", "")).strip()
    return epic_summary or None


def _extract_project_name(fields: dict[str, Any]) -> str | None:
    project = fields.get("project")
    if not isinstance(project, dict):
        return None
    name = str(project.get("name", "")).strip()
    return name or None


def _build_epic_preface(*, epic_summary: str | None, project_name: str | None) -> str | None:
    if not epic_summary:
        return None
    if not project_name:
        return epic_summary

    # Prefix with project context when epic summary alone may be ambiguous.
    if project_name.lower() in epic_summary.lower():
        return epic_summary
    return f"{project_name} - {epic_summary}"


def _is_issue_assigned_to_target(issue: dict[str, Any], target_account_id: str, target_email: str) -> bool:
    fields = issue.get("fields", {})
    assignee = fields.get("assignee")
    if not isinstance(assignee, dict):
        return False

    if assignee.get("accountId") == target_account_id:
        return True

    email = str(assignee.get("emailAddress", "")).lower()
    return email == target_email.lower()
