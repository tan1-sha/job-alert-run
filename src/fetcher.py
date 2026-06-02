import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Any

import requests

from src import config

log = logging.getLogger(__name__)


def _job_id(company: str, title: str, url: str) -> str:
    raw = f"{company.lower().strip()}|{title.lower().strip()}|{url.strip()}"
    return hashlib.sha1(raw.encode()).hexdigest()


def _normalize(
    *,
    title: str,
    company: str,
    location: str,
    description: str,
    url: str,
    source: str,
    date_posted: str | None = None,
) -> dict[str, Any]:
    return {
        "id": _job_id(company, title, url),
        "title": title.strip(),
        "company": company.strip(),
        "location": location.strip(),
        "description": description or "",
        "url": url.strip(),
        "source": source,
        "date_posted": date_posted or datetime.now(timezone.utc).isoformat(),
    }


# ── JobSpy ────────────────────────────────────────────────────────────────────

def fetch_jobspy() -> list[dict]:
    try:
        from jobspy import scrape_jobs  # type: ignore
    except ImportError:
        log.warning("python-jobspy not installed, skipping")
        return []

    results: list[dict] = []
    for term in config.SEARCH_TERMS:
        for location in config.LOCATIONS[:2]:  # SF + NYC to stay under rate limits
            try:
                df = scrape_jobs(
                    site_name=["indeed", "linkedin", "glassdoor", "zip_recruiter"],
                    search_term=term,
                    location=location,
                    results_wanted=config.RESULTS_PER_QUERY,
                    hours_old=config.HOURS_OLD,
                    verbose=0,
                )
                for _, row in df.iterrows():
                    results.append(_normalize(
                        title=str(row.get("title", "")),
                        company=str(row.get("company", "")),
                        location=str(row.get("location", "")),
                        description=str(row.get("description", "")),
                        url=str(row.get("job_url", "")),
                        source=f"jobspy/{row.get('site', 'unknown')}",
                        date_posted=str(row.get("date_posted", "")),
                    ))
                time.sleep(2)  # be polite between queries
            except Exception as exc:
                log.warning("jobspy error for %r @ %r: %s", term, location, exc)
    return results


# ── Adzuna ────────────────────────────────────────────────────────────────────

ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs/us/search/1"

def fetch_adzuna() -> list[dict]:
    results: list[dict] = []
    for term in config.SEARCH_TERMS:
        try:
            resp = requests.get(
                ADZUNA_BASE,
                params={
                    "app_id": config.ADZUNA_APP_ID,
                    "app_key": config.ADZUNA_APP_KEY,
                    "results_per_page": 50,
                    "what": term,
                    "where": "San Francisco",
                    "full_time": 1,
                    "sort_by": "date",
                },
                timeout=15,
            )
            resp.raise_for_status()
            for job in resp.json().get("results", []):
                results.append(_normalize(
                    title=job.get("title", ""),
                    company=job.get("company", {}).get("display_name", ""),
                    location=job.get("location", {}).get("display_name", ""),
                    description=job.get("description", ""),
                    url=job.get("redirect_url", ""),
                    source="adzuna",
                    date_posted=job.get("created", ""),
                ))
        except Exception as exc:
            log.warning("adzuna error for %r: %s", term, exc)
    return results


# ── Greenhouse ────────────────────────────────────────────────────────────────

def fetch_greenhouse(slug: str) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        jobs = []
        for job in resp.json().get("jobs", []):
            jobs.append(_normalize(
                title=job.get("title", ""),
                company=slug.title(),
                location=job.get("location", {}).get("name", ""),
                description=job.get("content", ""),
                url=job.get("absolute_url", ""),
                source=f"greenhouse/{slug}",
                date_posted=job.get("updated_at", ""),
            ))
        return jobs
    except Exception as exc:
        log.warning("greenhouse/%s error: %s", slug, exc)
        return []


# ── Lever ─────────────────────────────────────────────────────────────────────

def fetch_lever(slug: str) -> list[dict]:
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        jobs = []
        for job in resp.json():
            cats = job.get("categories", {})
            description = job.get("descriptionPlain", "") or job.get("description", "")
            jobs.append(_normalize(
                title=job.get("text", ""),
                company=slug.title(),
                location=cats.get("location", ""),
                description=description,
                url=job.get("hostedUrl", ""),
                source=f"lever/{slug}",
            ))
        return jobs
    except Exception as exc:
        log.warning("lever/%s error: %s", slug, exc)
        return []


# ── Ashby ─────────────────────────────────────────────────────────────────────

def fetch_ashby(slug: str) -> list[dict]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        jobs = []
        for job in resp.json().get("jobs", []):
            jobs.append(_normalize(
                title=job.get("title", ""),
                company=slug.title(),
                location=job.get("location", ""),
                description=job.get("descriptionHtml", ""),
                url=job.get("jobUrl", ""),
                source=f"ashby/{slug}",
                date_posted=job.get("publishedAt", ""),
            ))
        return jobs
    except Exception as exc:
        log.warning("ashby/%s error: %s", slug, exc)
        return []


# ── Orchestrator ──────────────────────────────────────────────────────────────

def fetch_all() -> list[dict]:
    jobs: list[dict] = []

    log.info("fetching jobspy…")
    jobs.extend(fetch_jobspy())

    log.info("fetching adzuna…")
    jobs.extend(fetch_adzuna())

    log.info("fetching greenhouse ATS feeds…")
    for slug in config.GREENHOUSE_SLUGS:
        jobs.extend(fetch_greenhouse(slug))
        time.sleep(0.3)

    log.info("fetching lever ATS feeds…")
    for slug in config.LEVER_SLUGS:
        jobs.extend(fetch_lever(slug))
        time.sleep(0.3)

    log.info("fetching ashby ATS feeds…")
    for slug in config.ASHBY_SLUGS:
        jobs.extend(fetch_ashby(slug))
        time.sleep(0.3)

    # deduplicate by id within this batch
    seen: set[str] = set()
    unique: list[dict] = []
    for job in jobs:
        if job["id"] not in seen:
            seen.add(job["id"])
            unique.append(job)

    log.info("fetched %d unique jobs total", len(unique))
    return unique
