import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from notion_client import Client

from src import config

log = logging.getLogger(__name__)

_client: Optional[Client] = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(auth=config.NOTION_TOKEN)
    return _client


def _fp(company: str, title: str) -> str:
    raw = f"{company.lower().strip()}|{title.lower().strip()}"
    return "fp:" + hashlib.sha1(raw.encode()).hexdigest()


def _fetch_all_pages() -> list[dict]:
    """Fetch every non-archived page from the Notion DB."""
    pages, cursor = [], None
    while True:
        kwargs: dict = {"database_id": config.NOTION_DB_ID, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = _get_client().databases.query(**kwargs)
        pages.extend(resp["results"])
        if not resp["has_more"]:
            break
        cursor = resp["next_cursor"]
    return pages


def sync() -> set[str]:
    """
    Run at the start of every job-alert cycle.

    1. Fetches all live Notion rows.
    2. Archives any row whose job title now fails the current filter
       (cleans up stale entries from before filter improvements).
    3. Returns the set of fingerprints still alive in Notion
       so the caller can skip re-adding them.
    """
    from src.filter import classify  # late import avoids circular

    pages = _fetch_all_pages()
    log.info("notion sync: %d live rows found", len(pages))

    alive_fps: set[str] = set()
    archived = 0

    for p in pages:
        props = p["properties"]

        title_arr   = props.get("Job title", {}).get("title", [])
        company_arr = props.get("Company",   {}).get("rich_text", [])
        location_arr = props.get("Location", {}).get("rich_text", [])

        title    = title_arr[0]["plain_text"]    if title_arr    else ""
        company  = company_arr[0]["plain_text"]  if company_arr  else ""
        location = location_arr[0]["plain_text"] if location_arr else ""

        if not title and not company:
            # blank/broken row — archive it
            _archive(p["id"])
            archived += 1
            continue

        job = {"title": title, "company": company.lower(),
               "location": location, "description": "", "url": ""}
        bucket, _ = classify(job)

        if bucket == "SKIP":
            _archive(p["id"])
            archived += 1
            log.debug("notion sync: archived stale %r @ %r", title, company)
        else:
            alive_fps.add(_fp(company, title))

    if archived:
        log.info("notion sync: archived %d stale rows", archived)

    log.info("notion sync: %d valid rows remain, %d fingerprints loaded",
             len(pages) - archived, len(alive_fps))
    return alive_fps


def _archive(page_id: str) -> None:
    try:
        _get_client().pages.update(page_id, archived=True)
        time.sleep(0.12)  # stay under Notion rate limit (3 req/s)
    except Exception as exc:
        log.warning("notion: archive failed for %s: %s", page_id, exc)


def add_row(job: dict, bucket: str, reason: str) -> None:
    location = job["location"][:200]
    why = f"[{bucket}] {reason}"[:200]
    date_str = datetime.now(timezone.utc).date().isoformat()

    # Strip HTML from description before storing; Notion rich_text max = 2000 chars
    import re as _re
    raw_desc = job.get("description", "") or ""
    plain_desc = _re.sub(r"<[^>]+>", " ", raw_desc)
    plain_desc = _re.sub(r"&[a-z]+;|&#\d+;", " ", plain_desc, flags=_re.IGNORECASE)
    plain_desc = " ".join(plain_desc.split())[:2000]  # collapse whitespace, cap

    props: dict = {
        "Job title": {
            "title": [{"text": {"content": job["title"][:200]}}]
        },
        "Company": {
            "rich_text": [{"text": {"content": job["company"][:100]}}]
        },
        "Source": {
            "rich_text": [{"text": {"content": job.get("source", "")[:100]}}]
        },
        "Link": {
            "url": job["url"] or None
        },
        "Location": {
            "rich_text": [{"text": {"content": location}}]
        },
        # E-verify intentionally omitted — fill manually when researching company
        "Bucket": {
            "select": {"name": bucket}
        },
        "Why flagged": {
            "rich_text": [{"text": {"content": why}}]
        },
        "Date found": {
            "date": {"start": date_str}
        },
        "Applied": {
            "checkbox": False
        },
        "Job Description": {
            "rich_text": [{"text": {"content": plain_desc}}] if plain_desc else []
        },
    }

    try:
        _get_client().pages.create(
            parent={"database_id": config.NOTION_DB_ID},
            properties=props,
        )
        log.info("notion: added %r @ %r", job["title"], job["company"])
    except Exception as exc:
        log.error("notion: failed to add %r: %s", job["title"], exc)
