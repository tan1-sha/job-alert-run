import re

from src import config

Bucket = str  # "STRONG" | "REVIEW" | "SKIP"

_HTML_TAG = re.compile(r"<[^>]+>")
_HTML_ENTITY = re.compile(r"&[a-z]+;|&#\d+;", re.IGNORECASE)
_MD_ESCAPE = re.compile(r"\\([+*#\-()\[\]!.`{}|<>_])")


def _clean(text: str) -> str:
    """Strip HTML, entities, and markdown escapes so regex matches plain text."""
    text = _HTML_TAG.sub(" ", text)
    text = _HTML_ENTITY.sub(" ", text)
    text = _MD_ESCAPE.sub(r"\1", text)   # \+ → +, \* → *, etc.
    return text


def classify(job: dict) -> tuple[Bucket, str]:
    """Return (bucket, reason) for a job.

    Filter order matters — hard cuts run before soft signals.
    Profile: entry-level new grad, F-1 OPT, USA only (or explicit visa offer).
    """
    title       = job["title"].strip()
    company     = job["company"].lower().strip()
    location    = job["location"].strip()
    description = _clean(job.get("description", "") or "")
    full_text   = f"{title} {description}"

    # ── 0. Staffing / contract agency — not a direct employer job ────────────
    if config.STAFFING_AGENCY_BLOCK.search(company):
        return "SKIP", f"staffing/contract agency: {company}"

    # ── 1. Wrong role type (non-digital / irrelevant designer) ───────────────
    if config.TITLE_ROLE_BLOCK.search(title):
        return "SKIP", "wrong role type (visual/motion/graphic/brand/accessory/non-digital)"

    # ── 2. Title must match a digital design role ─────────────────────────────
    if not config.TITLE_REQUIRED.search(title):
        return "SKIP", "title not a digital product design role"

    # ── 3. Too senior for entry-level candidate ───────────────────────────────
    if config.TITLE_SENIORITY_BLOCK.search(title):
        return "SKIP", "too senior (senior/staff/principal/lead/director/manager)"

    # ── 3a. Founding designer → SKIP (almost always expects 5+ yrs despite startup framing)
    # Checked early, before location/sponsorship — those can return REVIEW first and let a
    # founding-designer role slip through to Telegram if checked later in the pipeline.
    if config.TITLE_FOUNDING.search(title):
        return "SKIP", "founding designer — typically expects senior-level experience"

    # ── 3b. Non-Latin script in description → posting not written for US/India audience
    non_latin_count = len(config.NON_LATIN_SCRIPT.findall(description))
    if non_latin_count >= 15:
        return "SKIP", f"description in non-English script ({non_latin_count} non-Latin chars) — not US/India"

    # ── 5. Description hard-outs (citizenship/clearance/1099) ─────────────────
    # Checked before location: an empty/ambiguous location used to short-circuit straight
    # to REVIEW here, which meant a job with a hard-out (or a senior/over-experienced
    # requirement below) never got evaluated against those signals at all — see step 6.
    for pat in config.HARD_OUT_PATTERNS:
        if pat.search(full_text):
            return "SKIP", f"hard-out: {pat.pattern[:60]}"

    # ── 6. Experience year gates ──────────────────────────────────────────────
    # If description explicitly says entry-level / new grad → trust it, bypass year check.
    # Otherwise: any 2+ year requirement → SKIP.
    # Also catches qualitative seniority language (no year count) → REVIEW.
    # Deliberately runs before the location check (step 4) — a job with no/ambiguous
    # location info shouldn't get a free pass past an obvious "5-8+ years, Senior
    # Product Designer" requirement just because geography couldn't be confirmed yet.
    desc_missing = not description.strip()
    if not desc_missing:
        entry_level = config.ENTRY_LEVEL_SIGNAL.search(description)
        if not entry_level:
            desc_for_exp = config.COMPANY_AGE_MENTION.sub(" ", description)
            m = config.EXPERIENCE_SKIP.search(desc_for_exp)
            if m:
                snippet = description[max(0, m.start()-15):m.end()+15].strip()
                return "SKIP", f"experience req too high: «{snippet[:80]}»"
            # No explicit year count — check for qualitative seniority signals
            s = config.DESCRIPTION_SENIORITY_SIGNALS.search(description)
            if s:
                snippet = description[max(0, s.start()-10):s.end()+10].strip()
                return "REVIEW", f"seniority language in description — verify level: «{snippet[:80]}»"

    # ── 4. Location check ─────────────────────────────────────────────────────
    is_india       = config.INDIA_LOCATION.search(location)
    is_us          = config.USA_LOCATION.search(location)
    # Bare "Remote" matches USA_LOCATION but isn't geographically confirmed US —
    # treat as ambiguous so we still check the description for country signals.
    is_remote_only = bool(re.match(r"^\s*remote\s*$", location, re.IGNORECASE))
    is_confirmed_us = bool(is_us and not is_remote_only)

    if not location.strip():
        if not description.strip():
            return "REVIEW", "no description and empty location — verify manually"
        return "REVIEW", "empty location — verify geography manually"

    if is_india:
        # India path: Bengaluru tier-1 only, no US visa checks needed
        if company not in config.INDIA_TIER1_COMPANIES:
            return "SKIP", f"India job, not tier-1 company: {job['company']}"
        # Fall through to experience/seniority checks
    else:
        non_us_in_location = config.NON_US_LOCATION.search(location)
        non_us_in_text = config.NON_US_LOCATION.search(full_text)
        if location and not is_us:
            # Explicit non-US location
            if config.VISA_OFFER.search(full_text):
                return "REVIEW", f"non-US location but offers visa/OPT support: {location}"
            return "SKIP", f"non-US location, no visa mention: {location}"
        # Location field has non-US signal even though it also matched US (e.g. "Remote - UK")
        if non_us_in_location:
            if config.VISA_OFFER.search(full_text):
                return "REVIEW", f"non-US/non-India signal in location: {non_us_in_location.group()}"
            return "SKIP", f"non-US location signal: {non_us_in_location.group()}"
        if non_us_in_text and not is_confirmed_us:
            # Description/title mentions a foreign country — fires on Remote jobs too
            if config.INDIA_LOCATION.search(non_us_in_text.group()):
                # Remote job whose description mentions India → tier-1 gate
                if company not in config.INDIA_TIER1_COMPANIES:
                    return "SKIP", f"India remote job, not tier-1 company: {job['company']}"
            elif config.VISA_OFFER.search(full_text):
                return "REVIEW", f"non-US/non-India signals in description: {non_us_in_text.group()}"
            else:
                return "SKIP", f"non-US/non-India signals in description: {non_us_in_text.group()}"
        # Non-US currency or timezone in description → likely non-US employer posting "Remote"
        if not is_confirmed_us:
            tz_m = config.NON_US_TIMEZONE.search(description)
            fx_m = config.NON_USD_CURRENCY.search(description)
            signal = tz_m or fx_m
            if signal:
                if config.VISA_OFFER.search(full_text):
                    return "REVIEW", f"non-US timezone/currency in description: {signal.group()}"
                return "SKIP", f"non-US timezone/currency in description: {signal.group()}"

    # ── 7. Soft sponsorship flags → REVIEW (US jobs only) ────────────────────
    if not is_india:
        for pat in config.REVIEW_PATTERNS:
            if pat.search(full_text):
                return "REVIEW", f"ambiguous sponsorship language: {pat.pattern[:60]}"

    # ── 8. No description was ever fetched → can't verify experience, flag manually
    # (rather than auto-STRONG just because nothing disqualified it).
    if desc_missing:
        return "REVIEW", "no description available — verify experience level manually"

    # ── 9. Passed all filters → STRONG ────────────────────────────────────────
    if company in config.PRIORITY_COMPANIES:
        return "STRONG", f"priority company: {job['company']}"

    return "STRONG", "passed all filters"
