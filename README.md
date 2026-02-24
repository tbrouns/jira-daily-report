# Jira Daily Report CLI

Generate daily summaries (only for days with logged work) for a selected month by combining Jira issue/worklog data with OpenAI `gpt-4.1`.

## Features

- Filters activity by target user email and month (`YYYY-MM`)
- Uses worklogs as the source of truth for day-level activity
- Pulls issue context:
  - title
  - description
  - comments
  - direct parent
  - direct subtasks
  - parent Epic (when available)
- Loads system prompt instructions from `prompts/system_instructions.md`
- Prints plain text blocks per day for easy timesheet copy/paste

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

## Environment Variables

- `JIRA_BASE_URL` e.g. `https://company.atlassian.net`
- `JIRA_EMAIL` Jira Cloud account email used for API auth
- `JIRA_API_TOKEN` Jira scoped API token
- `OPENAI_API_KEY` OpenAI API key
- `OPENAI_MODEL` default: `gpt-4.1`
- `OPENAI_TEMPERATURE` default: `0.2`
- `TIMEZONE` default: `Europe/Amsterdam`
- `SYSTEM_PROMPT_PATH` default: `prompts/system_instructions.md`

## Notes

- User lookup by email depends on Jira visibility permissions.
- The tool keeps full plain text from Jira rich text fields and ignores non-text-only rendering concerns.
