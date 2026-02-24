from __future__ import annotations

import argparse
import sys
from pathlib import Path

from jira_daily_report.config import ConfigError, load_config
from jira_daily_report.context_builder import build_daily_prompt
from jira_daily_report.date_utils import MonthParseError, parse_month
from jira_daily_report.formatter import format_day_block
from jira_daily_report.jira_client import JiraClient
from jira_daily_report.llm import LlmSummarizer


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="jira-daily-report",
        description="Generate daily Jira summaries for days with logged work in a month.",
    )
    parser.add_argument(
        "--user-email",
        required=False,
        help="Target Jira user email (defaults to JIRA_EMAIL from environment).",
    )
    parser.add_argument("--month", required=True, help="Month in YYYY-MM format")
    args = parser.parse_args()

    try:
        config = load_config()
        month_window = parse_month(args.month)
        system_prompt = _load_system_prompt(config.system_prompt_path)
    except (ConfigError, MonthParseError) as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    target_user_email = args.user_email or config.jira_email

    jira = JiraClient(
        base_url=config.jira_base_url,
        email=config.jira_email,
        api_token=config.jira_api_token,
    )
    llm = LlmSummarizer(
        api_key=config.openai_api_key,
        model=config.openai_model,
        temperature=config.openai_temperature,
    )

    try:
        user = jira.resolve_user(target_user_email)
        account_id = user.get("accountId")
        if not account_id:
            raise RuntimeError(f"Resolved user missing accountId for {target_user_email}")

        daily_issue_set = jira.get_issue_keys_with_worklogs_for_month(
            month_start=month_window.start,
            month_end=month_window.end,
            target_account_id=account_id,
            target_email=target_user_email,
            timezone=config.timezone,
        )

        if not daily_issue_set.by_day_issue_seconds:
            print("No worklog activity found for the selected user/month.")
            return 0

        all_issue_keys = set().union(*[set(v.keys()) for v in daily_issue_set.by_day_issue_seconds.values()])
        epic_field_id = jira.detect_epic_link_field_id()
        issues_by_key = jira.get_issue_bundle(all_issue_keys, epic_field_id=epic_field_id)

        output_blocks: list[str] = []
        for day in sorted(daily_issue_set.by_day_issue_seconds):
            issue_seconds = daily_issue_set.by_day_issue_seconds[day]
            day_prompt = build_daily_prompt(
                day=day,
                issue_seconds=issue_seconds,
                issues_by_key=issues_by_key,
                jira_client=jira,
                epic_field_id=epic_field_id,
                target_account_id=account_id,
                target_email=target_user_email,
            )
            summary = llm.summarize_day(system_prompt=system_prompt, user_prompt=day_prompt)
            output_blocks.append(format_day_block(day=day, issue_seconds=issue_seconds, summary=summary))

        print("\n".join(output_blocks))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Execution failed: {exc}", file=sys.stderr)
        return 1


def _load_system_prompt(path: Path) -> str:
    if not path.exists():
        raise ConfigError(f"System prompt file does not exist: {path}")
    prompt = path.read_text(encoding="utf-8").strip()
    if not prompt:
        raise ConfigError(f"System prompt file is empty: {path}")
    return prompt


if __name__ == "__main__":
    raise SystemExit(main())
