from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from jira_daily_report.jira_client import DailyIssueSet


@dataclass(frozen=True)
class WorklogCacheEntry:
    month: str
    target_user_email: str
    timezone: str
    by_day_issue_seconds: dict[str, dict[str, int]]

    @classmethod
    def from_daily_issue_set(
        cls,
        *,
        month: str,
        target_user_email: str,
        timezone: str,
        daily_issue_set: DailyIssueSet,
    ) -> "WorklogCacheEntry":
        return cls(
            month=month,
            target_user_email=target_user_email,
            timezone=timezone,
            by_day_issue_seconds={
                day.isoformat(): dict(sorted(issue_seconds.items()))
                for day, issue_seconds in sorted(daily_issue_set.by_day_issue_seconds.items())
            },
        )

    def to_daily_issue_set(self) -> DailyIssueSet:
        return DailyIssueSet(
            by_day_issue_seconds={
                date.fromisoformat(day): dict(issue_seconds)
                for day, issue_seconds in self.by_day_issue_seconds.items()
            }
        )


class WorklogCache:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir

    def path_for(self, *, month: str, target_user_email: str) -> Path:
        safe_email = re.sub(r"[^a-zA-Z0-9._-]+", "_", target_user_email.strip().lower()).strip("._-") or "unknown"
        return self.root_dir / f"{month}_{safe_email}.json"

    def load(self, *, month: str, target_user_email: str, timezone: str) -> DailyIssueSet | None:
        path = self.path_for(month=month, target_user_email=target_user_email)
        if not path.exists():
            return None

        payload = json.loads(path.read_text(encoding="utf-8"))
        entry = WorklogCacheEntry(**payload)
        if (
            entry.month != month
            or entry.target_user_email.lower() != target_user_email.lower()
            or entry.timezone != timezone
        ):
            return None
        return entry.to_daily_issue_set()

    def save(
        self,
        *,
        month: str,
        target_user_email: str,
        timezone: str,
        daily_issue_set: DailyIssueSet,
    ) -> Path:
        path = self.path_for(month=month, target_user_email=target_user_email)
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = WorklogCacheEntry.from_daily_issue_set(
            month=month,
            target_user_email=target_user_email,
            timezone=timezone,
            daily_issue_set=daily_issue_set,
        )
        path.write_text(json.dumps(asdict(entry), indent=2, sort_keys=True), encoding="utf-8")
        return path

    def delete(self, *, month: str, target_user_email: str) -> None:
        path = self.path_for(month=month, target_user_email=target_user_email)
        if path.exists():
            path.unlink()
