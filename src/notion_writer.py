import logging
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


def add_row(job: dict, bucket: str, reason: str, everify: Optional[bool]) -> None:
    from src.everify import enrolled_label

    ev_label = enrolled_label(everify)

    # Truncate location/reason to Notion's 2000-char rich_text limit
    location = job["location"][:200]
    why = f"[{bucket}] {reason}"[:200]
    date_str = datetime.now(timezone.utc).date().isoformat()

    props: dict = {
        "Job Title": {
            "title": [{"text": {"content": job["title"][:200]}}]
        },
        "Company": {
            "rich_text": [{"text": {"content": job["company"][:100]}}]
        },
        "Link": {
            "url": job["url"] or None
        },
        "Location": {
            "rich_text": [{"text": {"content": location}}]
        },
        "E-Verify": {
            "select": {"name": ev_label}
        },
        "Bucket": {
            "select": {"name": bucket}
        },
        "Why Flagged": {
            "rich_text": [{"text": {"content": why}}]
        },
        "Date Found": {
            "date": {"start": date_str}
        },
        "Applied": {
            "checkbox": False
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
