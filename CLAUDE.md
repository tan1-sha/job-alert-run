# Project: job-alert-run

## Security rules

**NEVER read, print, log, or access credentials, API keys, tokens, or secrets from .env, GitHub secrets, or any config.**
Always ask the user for permission before touching anything secret-related.

## Stack

- Python 3.12, GitHub Actions (cron every 4h at `17 */4 * * *`)
- Sources: JobSpy, Adzuna API, Greenhouse/Lever/Ashby ATS endpoints
- Outputs: **Telegram fires for both STRONG and REVIEW** (`main.py` calls
  `telegram_notify.send_strong`/`send_review` for both buckets — despite what
  it sounds like, REVIEW is not Notion-only). Notion gets STRONG + REVIEW.
- Dedup: `data/seen_jobs.json` committed back to repo after each run

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m src.main
```

## Filtering architecture

All classification lives in two files:
- `src/config.py` — every regex/keyword list (locations, seniority, hard-outs, visa)
- `src/filter.py` — `classify(job) -> (bucket, reason)`, the single decision pipeline

Candidate profile the filters are tuned for: entry-level new grad, F-1 OPT
(needs W-2 USA jobs or explicit visa sponsorship), USA + India (tier-1
companies only) — see `config.py` header comment for current details.

**Filter order is deliberate, not arbitrary.** Title/seniority/hard-out/experience
checks all run *before* the location check, specifically so a senior or
over-experienced job doesn't get a free pass to REVIEW just because its
location was ambiguous. Don't reorder steps in `classify()` without re-reading
the inline rationale comments — at least two past bugs were exactly this class
of "ambiguous signal masks a real disqualifier" ordering mistake.

**`src/cleanup_notion.py` re-implements a chunk of `classify()`'s logic by hand**
(title/location/experience checks against *live* Notion rows, including
re-fetching descriptions from job URLs) instead of calling `classify()`
directly. This is a real footgun: any new rule added to `filter.py`/`config.py`
must be manually mirrored into `cleanup_notion.py`'s `should_archive()`, or newly
tightened rules will silently not apply to already-existing Notion rows. Found
and fixed one instance of this drift already (2026-08-06): the India tier-1
company gate existed in `classify()` but not in `should_archive()`, so running
cleanup wrongly archived legitimate Bengaluru rows from Google/Adobe/slice
before the fix. **Always test `cleanup_notion.py` changes against known-good
tier-1/India rows before running it for real** — it mutates the live Notion DB
and archiving is not obvious to undo without page IDs from the run log.

`notion_writer.sync()` (runs every cycle, separate from `cleanup_notion.py`)
reclassifies existing Notion rows with `description=""`/`url=""` — so any
description-dependent rule (hard-outs, experience years, visa negation,
non-Latin script) is invisible to it. Only title/location rules actually
archive stale rows during normal sync.

## Known regex-system limits (not bugs, just can't be auto-solved)

- Leveling codes (L3/L4/IC3/IC4/"Designer II") are company-specific — routed to
  REVIEW with a reason, not auto-SKIP, since some companies use those for
  entry-level. L5+/IC5+/"Designer III+" are auto-SKIP (unambiguous).
- "Remote - Worldwide/Global/International/Anywhere" location tags are
  ambiguous (could be a US company hiring globally) → REVIEW, not SKIP.
- Jobs with no fetched description always land as REVIEW (never auto-STRONG)
  since none of the description-based checks ran.
- `INDIA_TIER1_COMPANIES`/`PRIORITY_COMPANIES` in `config.py` are static
  hardcoded sets — they will drift as companies open/close offices or hiring
  focus changes. No automatic sync; review periodically.

## Notion review workflow

REVIEW rows get their `classify()` reason written into the **Notes** field
(`notion_writer.add_row`, only for bucket=="REVIEW" — STRONG reasons are
usually just "passed all filters" and not worth cluttering Notes with).
Filter/sort by `Bucket = REVIEW` then read `Notes` to know exactly what to
check instead of reopening every posting cold. This only applies to rows added
2026-08-06 onward — existing rows before that date have blank Notes.