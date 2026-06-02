from src import config

Bucket = str  # "STRONG" | "REVIEW" | "SKIP"


def _full_text(job: dict) -> str:
    return f"{job['title']} {job['description']}"


def classify(job: dict) -> tuple[Bucket, str]:
    """Return (bucket, reason) for a job.

    Filter order matters — hard cuts run before soft signals.
    Profile: entry-level new grad, F-1 OPT, USA only (or explicit visa offer).
    """
    title       = job["title"].strip()
    company     = job["company"].lower().strip()
    location    = job["location"].strip()
    description = job["description"]
    full_text   = f"{title} {description}"

    # ── 1. Wrong role type (non-digital designer) ─────────────────────────────
    if config.TITLE_ROLE_BLOCK.search(title):
        return "SKIP", "wrong role type (motion/graphic/brand/non-digital)"

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
            return "SKIP", f"hard-out description: {pat.pattern[:60]}"

    # ── 6. Soft sponsorship flags → REVIEW ────────────────────────────────────
    for pat in config.REVIEW_PATTERNS:
        if pat.search(full_text):
            return "REVIEW", f"ambiguous sponsorship language: {pat.pattern[:60]}"

    # ── 7. Founding designer → REVIEW (often expects senior despite framing) ──
    if config.TITLE_FOUNDING.search(title):
        return "REVIEW", "founding designer role — may expect more experience, review manually"

    # ── 8. Passed all filters → STRONG ────────────────────────────────────────
    if company in config.PRIORITY_COMPANIES:
        return "STRONG", f"priority company: {job['company']}"

    return "STRONG", "passed all filters"
