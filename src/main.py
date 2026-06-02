"""Entry point. Run: python -m src.main"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from src import config, everify, fetcher, filter as filt, notion_writer, telegram_notify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("main")


def load_seen() -> set[str]:
    path = Path(config.SEEN_JOBS_PATH)
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text())
        return set(data.get("ids", []))
    except Exception:
        return set()


def save_seen(ids: set[str]) -> None:
    path = Path(config.SEEN_JOBS_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "ids": sorted(ids),
        "last_run": datetime.now(timezone.utc).isoformat(),
    }, indent=2))


def run() -> None:
    seen_ids = load_seen()
    log.info("loaded %d seen job IDs", len(seen_ids))

    all_jobs = fetcher.fetch_all()

    new_jobs = [j for j in all_jobs if j["id"] not in seen_ids]
    log.info("%d new jobs after dedup", len(new_jobs))

    counts = {"STRONG": 0, "REVIEW": 0, "SKIP": 0}

    for job in new_jobs:
        bucket, reason = filt.classify(job)
        counts[bucket] += 1

        if bucket == "SKIP":
            seen_ids.add(job["id"])
            continue

        ev = everify.lookup(job["company"])

        if bucket == "STRONG":
            telegram_notify.send_strong(job, ev, reason)
            notion_writer.add_row(job, bucket, reason, ev)
        elif bucket == "REVIEW":
            notion_writer.add_row(job, bucket, reason, ev)

        seen_ids.add(job["id"])

    log.info("results → STRONG: %d  REVIEW: %d  SKIP: %d", *counts.values())
    save_seen(seen_ids)
    log.info("seen_jobs.json updated (%d total IDs)", len(seen_ids))


if __name__ == "__main__":
    run()
