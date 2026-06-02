from src import config

Bucket = str  # "STRONG" | "REVIEW" | "SKIP"


def _text(job: dict) -> str:
    return f"{job['title']} {job['description']}".lower()


def classify(job: dict) -> tuple[Bucket, str]:
    """Return (bucket, reason) for a job."""
    title = job["title"]
    company = job["company"].lower().strip()
    text = _text(job)

    # 1. title must match design roles
    if not config.TITLE_KEYWORDS.search(title):
        return "SKIP", "title not design role"

    # 2. hard-out patterns → SKIP
    for pat in config.HARD_OUT_PATTERNS:
        if pat.search(text):
            return "SKIP", f"hard-out: {pat.pattern[:60]}"

    # 3. soft-flag patterns → REVIEW
    for pat in config.REVIEW_PATTERNS:
        if pat.search(text):
            return "REVIEW", f"ambiguous sponsorship language: {pat.pattern[:60]}"

    # 4. passed all filters → STRONG (boost if priority company)
    if company in config.PRIORITY_COMPANIES:
        return "STRONG", f"priority company: {job['company']}"

    return "STRONG", "passed all filters"
