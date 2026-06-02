# Project: job-alert-run

## Security rules

**NEVER read, print, log, or access credentials, API keys, tokens, or secrets from .env, GitHub secrets, or any config.**
Always ask the user for permission before touching anything secret-related.

## Stack

- Python 3.12, GitHub Actions (cron every 4h at `17 */4 * * *`)
- Sources: JobSpy, Adzuna API, Greenhouse/Lever/Ashby ATS endpoints
- Outputs: Telegram (STRONG matches), Notion database (STRONG + REVIEW)
- Dedup: `data/seen_jobs.json` committed back to repo after each run

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.main
```
