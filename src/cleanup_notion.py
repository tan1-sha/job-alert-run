"""
One-shot Notion cleanup — with live URL description fetching.
- Archives rows with any "Not a fit — why?" chip selected
- Archives rows where description (stored OR fetched from link) contains
  2+ year requirements or senior-level language
Run: python -m src.cleanup_notion
"""
import logging
import sys
import time

from src.filter import _clean
from src.notion_writer import _archive, _fetch_all_pages, _get_client
from src.config import (
    EXPERIENCE_SKIP, ENTRY_LEVEL_SIGNAL, DESCRIPTION_SENIORITY_SIGNALS,
    TITLE_SENIORITY_BLOCK, TITLE_ROLE_BLOCK, TITLE_REQUIRED, NOTION_DB_ID,
    STAFFING_AGENCY_BLOCK,
)
from src.fetcher import _fetch_description_from_ats_url

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s — %(message)s", stream=sys.stdout)
log = logging.getLogger("cleanup")


def _check_description(description: str) -> tuple[bool, str]:
    """Return (should_archive, reason) based on description text."""
    desc = _clean(description)
    if not desc.strip():
        return False, ""
    if ENTRY_LEVEL_SIGNAL.search(desc):
        return False, ""  # explicit entry-level language — keep
    m = EXPERIENCE_SKIP.search(desc)
    if m:
        snippet = desc[max(0, m.start()-10):m.end()+10].strip()
        return True, f"description: 2+ years req — «{snippet[:70]}»"
    s = DESCRIPTION_SENIORITY_SIGNALS.search(desc)
    if s:
        snippet = desc[max(0, s.start()-10):s.end()+10].strip()
        return True, f"description: senior language — «{snippet[:70]}»"
    return False, ""


def _update_description(page_id: str, desc: str) -> None:
    """Write fetched description back to the Notion row for future runs."""
    plain = _clean(desc)
    plain = " ".join(plain.split())[:2000]
    try:
        _get_client().pages.update(
            page_id,
            properties={"Job Description": {"rich_text": [{"text": {"content": plain}}]}},
        )
    except Exception as exc:
        log.debug("could not update description for %s: %s", page_id, exc)


def should_archive(page: dict) -> tuple[bool, str]:
    props = page.get("properties", {})

    # ── 1. User explicitly flagged it ────────────────────────────────────────
    feedback = props.get("Not a fit — why?", {}).get("multi_select", [])
    if feedback:
        labels = [f["name"] for f in feedback]
        return True, f"user feedback: {', '.join(labels)}"

    # ── 2. Title + company filters ────────────────────────────────────────────
    title_arr = props.get("Job title", {}).get("title", [])
    title = title_arr[0]["plain_text"] if title_arr else ""
    company_arr = props.get("Company", {}).get("rich_text", [])
    company = company_arr[0]["plain_text"] if company_arr else ""

    if STAFFING_AGENCY_BLOCK.search(company):
        return True, f"staffing/contract agency: {company}"
    if TITLE_ROLE_BLOCK.search(title):
        return True, "title: wrong role type"
    if not TITLE_REQUIRED.search(title):
        return True, "title: not a digital design role"
    if TITLE_SENIORITY_BLOCK.search(title):
        return True, "title: too senior"

    # ── 3. Stored description ────────────────────────────────────────────────
    desc_arr = props.get("Job Description", {}).get("rich_text", [])
    stored_desc = desc_arr[0]["plain_text"] if desc_arr else ""
    archive, reason = _check_description(stored_desc)
    if archive:
        return True, reason

    # ── 4. Fetch live description from job URL if stored is empty ─────────────
    if not stored_desc.strip():
        link_prop = props.get("Link", {})
        url = link_prop.get("url") or ""
        if url:
            live_desc = _fetch_description_from_ats_url(url)
            if live_desc.strip():
                # Write back so future runs don't re-fetch
                _update_description(page["id"], live_desc)
                archive, reason = _check_description(live_desc)
                if archive:
                    return True, reason

    return False, ""


def run():
    pages = _fetch_all_pages()
    log.info("fetched %d live rows from Notion", len(pages))

    archived = 0
    kept = 0
    no_desc = 0

    for p in pages:
        props = p.get("properties", {})
        title_arr = props.get("Job title", {}).get("title", [])
        title = title_arr[0]["plain_text"] if title_arr else "?"
        company_arr = props.get("Company", {}).get("rich_text", [])
        company = company_arr[0]["plain_text"] if company_arr else "?"

        do_archive, reason = should_archive(p)

        if do_archive:
            log.info("ARCHIVE  %r @ %r  — %s", title, company, reason)
            _archive(p["id"])
            archived += 1
        else:
            # Check if description is still empty after fetch attempt
            desc_arr = props.get("Job Description", {}).get("rich_text", [])
            if not (desc_arr[0]["plain_text"] if desc_arr else "").strip():
                no_desc += 1
                log.debug("no-desc  %r @ %r", title, company)
            kept += 1

        time.sleep(0.3)  # rate limit: Notion 3 req/s

    log.info("done — archived %d, kept %d (%d with no fetchable description)",
             archived, kept, no_desc)


if __name__ == "__main__":
    run()
