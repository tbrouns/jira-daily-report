from __future__ import annotations

from datetime import date


def format_day_block(day: date, issue_seconds: dict[str, int], summary: str) -> str:
    issue_list = ", ".join(sorted(issue_seconds))
    total_hours = sum(issue_seconds.values()) / 3600
    return "\n".join(
        [
            f"Date: {day.isoformat()}",
            f"Total Time Logged: {total_hours:.2f}h",
            f"Issues: {issue_list}",
            "Summary:",
            summary.strip(),
            "",
        ]
    )
