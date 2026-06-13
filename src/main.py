"""Entry point. Run: python -m src.main"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from src import config, fetcher, filter as filt, notion_writer, telegram_notify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("main")


def load_seen() -> tuple[set[str], set[str]]:
    """Returns (seen_ids, seen_fingerprints) from local cache."""
    path = Path(config.SEEN_JOBS_PATH)
    if not path.exists():
        return set(), set()
    try:
        data = json.loads(path.read_text())
        return set(data.get("ids", [])), set(data.get("fingerprints", []))
    except Exception:
        return set(), set()


def save_seen(ids: set[str], fingerprints: set[str]) -> None:
    path = Path(config.SEEN_JOBS_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "ids": sorted(ids),
        "fingerprints": sorted(fingerprints),
        "last_run": datetime.now(timezone.utc).isoformat(),
    }, indent=2))


def run() -> None:
    # ── Step 1: load local dedup cache ───────────────────────────────────────
    seen_ids, seen_fps = load_seen()
    log.info("loaded %d seen IDs, %d fingerprints from cache", len(seen_ids), len(seen_fps))

    # ── Step 2: Notion sync — clean stale rows, pull live fingerprints ────────
    # Archives Notion rows that now fail the filter (keeps DB tidy automatically).
    # Returns fingerprints of rows still alive → merged into seen_fps so we never
    # re-add a job already in Notion even if local cache was wiped.
    notion_fps = notion_writer.sync()
    seen_fps |= notion_fps

    # ── Step 3: fetch jobs from all sources ───────────────────────────────────
    all_jobs = fetcher.fetch_all()

    # ── Step 4: cross-run dedup — URL id AND content fingerprint ─────────────
    new_jobs = [
        j for j in all_jobs
        if j["id"] not in seen_ids and j["fingerprint"] not in seen_fps
    ]
    log.info("%d new jobs after dedup", len(new_jobs))

    # ── Step 5: classify and notify ───────────────────────────────────────────
    counts = {"STRONG": 0, "REVIEW": 0, "SKIP": 0}

    for job in new_jobs:
        bucket, reason = filt.classify(job)
        counts[bucket] += 1

        # Mark seen immediately — prevents double-processing if run crashes mid-way
        seen_ids.add(job["id"])
        seen_fps.add(job["fingerprint"])

        if bucket == "SKIP":
            continue

        if bucket == "STRONG":
            telegram_notify.send_strong(job, reason)
            notion_writer.add_row(job, bucket)
        elif bucket == "REVIEW":
            telegram_notify.send_review(job, reason)
            notion_writer.add_row(job, bucket)

    # ── Step 6: persist updated cache ─────────────────────────────────────────
    log.info("results → STRONG: %d  REVIEW: %d  SKIP: %d", *counts.values())
    save_seen(seen_ids, seen_fps)
    log.info("seen_jobs.json updated (%d IDs, %d fingerprints)", len(seen_ids), len(seen_fps))


if __name__ == "__main__":
    run()
