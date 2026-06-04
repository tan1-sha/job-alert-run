import re

from src import config

Bucket = str  # "STRONG" | "REVIEW" | "SKIP"

_HTML_TAG = re.compile(r"<[^>]+>")
_HTML_ENTITY = re.compile(r"&[a-z]+;|&#\d+;", re.IGNORECASE)


def _clean(text: str) -> str:
    """Strip HTML tags and entities so regex matches plain text."""
    text = _HTML_TAG.sub(" ", text)
    text = _HTML_ENTITY.sub(" ", text)
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

    # ── 1. Wrong role type (non-digital / irrelevant designer) ───────────────
    if config.TITLE_ROLE_BLOCK.search(title):
        return "SKIP", "wrong role type (visual/motion/graphic/brand/accessory/non-digital)"

    # ── 2. Title must match a digital design role ─────────────────────────────
    if not config.TITLE_REQUIRED.search(title):
        return "SKIP", "title not a digital product design role"

    # ── 3. Too senior for entry-level candidate ───────────────────────────────
    if config.TITLE_SENIORITY_BLOCK.search(title):
        return "SKIP", "too senior (senior/staff/principal/lead/director/manager)"

    # ── 4. Location: must be USA or explicitly offering visa ──────────────────
    if location and not config.USA_LOCATION.search(location):
        if config.VISA_OFFER.search(full_text):
            return "REVIEW", f"non-US location but offers visa/OPT support: {location}"
        return "SKIP", f"non-US location, no visa mention: {location}"

    # ── 5. Description hard-outs (citizenship/clearance/1099) ─────────────────
    for pat in config.HARD_OUT_PATTERNS:
        if pat.search(full_text):
            return "SKIP", f"hard-out: {pat.pattern[:60]}"

    # ── 6. Experience year gates ──────────────────────────────────────────────
    # EXPERIENCE_SKIP always wins — even if "entry-level" appears elsewhere in desc.
    # Some jobs say "entry-level welcome" then list "4+ years preferred" → still skip.
    # Exception: if BOTH signals fire, route to REVIEW for manual check instead of
    # hard-skipping (mixed signals could mean the high-year line is a "nice to have").
    if description.strip():
        m = config.EXPERIENCE_SKIP.search(description)
        if m:
            snippet = description[max(0, m.start()-15):m.end()+15].strip()
            if config.ENTRY_LEVEL_SIGNAL.search(description):
                return "REVIEW", f"mixed signals — entry-level language but high exp req: «{snippet[:80]}»"
            return "SKIP", f"experience req too high: «{snippet[:80]}»"
    else:
        # No description fetched — could be any level. Flag to review manually.
        return "REVIEW", "no description available — verify experience level manually"

    # ── 7. Soft sponsorship flags → REVIEW ────────────────────────────────────
    for pat in config.REVIEW_PATTERNS:
        if pat.search(full_text):
            return "REVIEW", f"ambiguous sponsorship language: {pat.pattern[:60]}"

    # ── 8. Founding designer → REVIEW (often expects senior despite startup framing)
    if config.TITLE_FOUNDING.search(title):
        return "REVIEW", "founding designer — verify experience level manually"

    # ── 9. Passed all filters → STRONG ────────────────────────────────────────
    if company in config.PRIORITY_COMPANIES:
        return "STRONG", f"priority company: {job['company']}"

    return "STRONG", "passed all filters"
