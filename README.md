# Jira Daily Report CLI

Generate monthly Jira reports for a selected user by combining Jira issue/worklog data with OpenAI `gpt-4.1`.

## Features

- Filters activity by target user email and month (`YYYY-MM`)
- Writes reports to `./reports` under the current working directory
- Uses worklogs as the source of truth for day-level activity
- Pulls issue context:
  - title
  - description
  - comments
  - direct parent
  - direct subtasks
  - parent Epic (when available), including Epic summary and project-name context
- Loads system prompt instructions from `prompts/system_instructions.md`
- Generates:
  - monthly spreadsheet report (Excel by default, CSV optional)
  - daily plain text summary report
- Applies a per-day summary character limit (default: `1500`) with truncation as last resort
- Summary output is high-level and grouped by unique `Project - Epic` preface (when available)

## Setup

1. Create and activate a Python virtualenv.
2. Install package:

```bash
pip install -e .
```

3. Create `.env` from `.env.example` and fill values.

## Run

```bash
jira-daily-report --user-email user@example.com --month 2026-01
```

or:

```bash
python -m jira_daily_report --user-email user@example.com --month 2026-01
```

CSV output:

```bash
jira-daily-report --user-email user@example.com --month 2026-01 --spreadsheet-format csv
```

Custom summary character limit:

```bash
jira-daily-report --user-email user@example.com --month 2026-01 --summary-char-limit 2000
```

## Output Files

For month `2026-01`, generated files are:

- `reports/jira_worklog_2026-01.xlsx` (or `.csv` with `--spreadsheet-format csv`)
- `reports/daily_summary_2026-01.txt`

Spreadsheet report:
- First column: Jira issue link
- Remaining columns: working days (Mon-Fri) in the selected month
- Each issue row contains decimal hours per day for that issue

Daily summary report:
- One entry per day with summarized work
- Format starts with day prefix: `YYYY-MM-DD - `
- Summary body is prompt-driven and grouped by unique `Project - Epic` preface where possible
- Prefaces and topic lines avoid date/time-window references in the summary body

## Environment Variables

- `JIRA_BASE_URL` e.g. `https://company.atlassian.net`
- `JIRA_EMAIL` Jira Cloud account email used for API auth
- `JIRA_API_TOKEN` Jira scoped API token
- `OPENAI_API_KEY` OpenAI API key
- `OPENAI_MODEL` default: `gpt-4.1`
- `OPENAI_TEMPERATURE` default: `0.2`
- `SUMMARY_CHAR_LIMIT` default: `1500`
- `TIMEZONE` default: `Europe/Amsterdam`
- `SYSTEM_PROMPT_PATH` default: `prompts/system_instructions.md`

## Notes

- User lookup by email depends on Jira visibility permissions.
- The tool keeps full plain text from Jira rich text fields and ignores non-text-only rendering concerns.
- If Jira context has no meaningful completed work for a day, that day can be omitted from the summary report.
