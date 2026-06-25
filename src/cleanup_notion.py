"""
One-shot Notion cleanup — with live URL description fetching.
- Archives rows with any "Not a fit — why?" chip selected
- Archives rows where description (stored OR fetched from link) contains
  2+ year requirements or senior-level language
Run: python -m src.cleanup_notion
"""
import logging
import re
import sys
import time

from src.filter import _clean
from src.notion_writer import _archive, _fetch_all_pages, _get_client
from src.config import (
    EXPERIENCE_SKIP, ENTRY_LEVEL_SIGNAL, DESCRIPTION_SENIORITY_SIGNALS,
    TITLE_SENIORITY_BLOCK, TITLE_ROLE_BLOCK, TITLE_REQUIRED, NOTION_DB_ID,
    STAFFING_AGENCY_BLOCK, NON_US_LOCATION, USA_LOCATION, VISA_OFFER,
    NON_LATIN_SCRIPT,
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


def _all_text(rich_text_arr: list) -> str:
    """Join every rich_text object's plain_text — descriptions are stored as
    multiple 2000-char chunks, not a single object."""
    return "".join(o.get("plain_text", "") for o in rich_text_arr)


def _update_description(page_id: str, desc: str) -> None:
    """Write fetched description back to the Notion row for future runs."""
    plain = _clean(desc)
    plain = " ".join(plain.split())[:200_000]
    chunks = [plain[i:i + 2000] for i in range(0, len(plain), 2000)]
    try:
        _get_client().pages.update(
            page_id,
            properties={"Job Description": {"rich_text": [{"text": {"content": c}} for c in chunks]}},
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

    # ── 3. Location check ────────────────────────────────────────────────────
    link_prop = props.get("Link", {})
    url = link_prop.get("url") or ""
    location_arr = props.get("Location", {}).get("rich_text", [])
    location = location_arr[0]["plain_text"] if location_arr else ""
    if location and not USA_LOCATION.search(location):
        if not VISA_OFFER.search(location):
            return True, f"non-US location: {location}"
    non_us_in_loc = NON_US_LOCATION.search(location)
    if non_us_in_loc:
        if not VISA_OFFER.search(location):
            return True, f"non-US location signal: {non_us_in_loc.group()}"

    # ── 4. Stored description ────────────────────────────────────────────────
    desc_arr = props.get("Job Description", {}).get("rich_text", [])
    stored_desc = _all_text(desc_arr)
    archive, reason = _check_description(stored_desc)
    if archive:
        return True, reason

    # ── 5. Fetch live description from job URL if stored is empty ─────────────
    if not stored_desc.strip():
        if url:
            live_desc = _fetch_description_from_ats_url(url)
            if live_desc.strip():
                _update_description(page["id"], live_desc)
                archive, reason = _check_description(live_desc)
                if archive:
                    return True, reason
                stored_desc = live_desc

    # ── 6. Non-Latin script in description → not written for US/India audience
    non_latin_count = len(NON_LATIN_SCRIPT.findall(_clean(stored_desc)))
    if non_latin_count >= 15:
        return True, f"description in non-English script ({non_latin_count} non-Latin chars)"

    # ── 7. Non-US signals in description (catches "Remote" from foreign companies)
    full_text = f"{title} {location} {stored_desc}"
    is_remote_only = bool(re.match(r"^\s*remote\s*$", location, re.IGNORECASE))
    is_confirmed_us = bool(USA_LOCATION.search(location or "") and not is_remote_only)
    non_us = NON_US_LOCATION.search(full_text)
    if non_us and not is_confirmed_us:
        if not VISA_OFFER.search(full_text):
            return True, f"non-US signals: {non_us.group()}"

    return False, ""  # keep


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
            if not _all_text(desc_arr).strip():
                no_desc += 1
                log.debug("no-desc  %r @ %r", title, company)
            kept += 1

        time.sleep(0.3)  # rate limit: Notion 3 req/s

    log.info("done — archived %d, kept %d (%d with no fetchable description)",
             archived, kept, no_desc)


if __name__ == "__main__":
    run()
