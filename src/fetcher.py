import hashlib
import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any

import requests

from src import config

log = logging.getLogger(__name__)

_BROWSER_HEADERS = {"User-Agent": "Mozilla/5.0"}


def _job_id(company: str, title: str, url: str) -> str:
    """URL-based ID — unique per source listing."""
    raw = f"{company.lower().strip()}|{title.lower().strip()}|{url.strip()}"
    return hashlib.sha1(raw.encode()).hexdigest()


def _fingerprint(company: str, title: str) -> str:
    """Content fingerprint — same job from multiple sources → same fingerprint."""
    raw = f"{company.lower().strip()}|{title.lower().strip()}"
    return "fp:" + hashlib.sha1(raw.encode()).hexdigest()


def _normalize(
    *,
    title: str,
    company: str,
    location: str,
    description: str,
    url: str,
    source: str,
    date_posted: str | None = None,
    job_type: str | None = None,
) -> dict[str, Any]:
    c, t = company.strip(), title.strip()
    return {
        "id": _job_id(c, t, url),
        "fingerprint": _fingerprint(c, t),
        "title": t,
        "company": c,
        "location": location.strip(),
        "description": description or "",
        "url": url.strip(),
        "source": source,
        "date_posted": date_posted or datetime.now(timezone.utc).isoformat(),
        "job_type": (job_type or "").strip().lower(),
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
        for location in config.LOCATIONS:  # all locations including Remote
            try:
                df = scrape_jobs(
                    site_name=["indeed", "linkedin", "glassdoor", "zip_recruiter"],
                    search_term=term,
                    location=location,
                    results_wanted=config.RESULTS_PER_QUERY,
                    hours_old=config.HOURS_OLD,
                    linkedin_fetch_description=True,  # extra request per job to get full description
                    verbose=0,
                )
                for _, row in df.iterrows():
                    job = _normalize(
                        title=str(row.get("title", "")),
                        company=str(row.get("company", "")),
                        location=str(row.get("location", "")),
                        description=str(row.get("description", "") or ""),
                        url=str(row.get("job_url", "")),
                        source=f"jobspy/{row.get('site', 'unknown')}",
                        date_posted=str(row.get("date_posted", "")),
                        job_type=str(row.get("job_type", "") or ""),
                    )
                    # Store direct ATS URL separately for description enrichment
                    direct = str(row.get("job_url_direct", "") or "")
                    if direct and direct != "nan":
                        job["url_direct"] = direct
                    results.append(job)
                time.sleep(2)  # be polite between queries
            except Exception as exc:
                log.warning("jobspy error for %r @ %r: %s", term, location, exc)
    return results


# ── Adzuna ────────────────────────────────────────────────────────────────────

ADZUNA_BASE       = "https://api.adzuna.com/v1/api/jobs/us/search/1"
ADZUNA_INDIA_BASE = "https://api.adzuna.com/v1/api/jobs/in/search/1"

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
                    job_type=job.get("contract_type", "") or job.get("contract_time", ""),
                ))
            time.sleep(1)
        except Exception as exc:
            log.warning("adzuna error for %r: %s", term, exc)
    return results


def fetch_adzuna_india() -> list[dict]:
    results: list[dict] = []
    for term in config.SEARCH_TERMS:
        try:
            resp = requests.get(
                ADZUNA_INDIA_BASE,
                params={
                    "app_id": config.ADZUNA_APP_ID,
                    "app_key": config.ADZUNA_APP_KEY,
                    "results_per_page": 50,
                    "what": term,
                    "where": "India",
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
                    source="adzuna/india",
                    date_posted=job.get("created", ""),
                ))
            time.sleep(1)
        except Exception as exc:
            log.warning("adzuna/india error for %r: %s", term, exc)
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


# ── Description enrichment via ATS direct URL ────────────────────────────────
# LinkedIn/Indeed block scraping so descriptions come back empty.
# JobSpy's job_url_direct often points to the actual company ATS page
# (Greenhouse / Lever / Ashby). We parse that URL and hit the public API
# to get the full description — same APIs we already use for slug polling.

import re as _re

_GH_URL   = _re.compile(r"boards(?:-api)?\.greenhouse\.io/(?:v1/boards/)?([^/]+)/jobs/(\d+)", _re.I)
_LV_URL   = _re.compile(r"jobs\.lever\.co/([^/]+)/([^/?]+)", _re.I)
_ASH_URL  = _re.compile(r"(?:jobs\.ashbyhq\.com|api\.ashbyhq\.com/posting-api/job-board)/([^/]+)(?:/postings?)?/([^/?]+)", _re.I)


def _fetch_description_from_ats_url(url: str) -> str:
    """Try to get description from an ATS URL. Returns empty string on failure."""
    if not url:
        return ""
    # Greenhouse
    m = _GH_URL.search(url)
    if m:
        slug, job_id = m.group(1), m.group(2)
        try:
            r = requests.get(
                f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job_id}?questions=true",
                timeout=8,
            )
            if r.ok:
                return r.json().get("content", "")
        except Exception:
            pass
    # Lever
    m = _LV_URL.search(url)
    if m:
        slug, job_id = m.group(1), m.group(2)
        try:
            r = requests.get(f"https://api.lever.co/v0/postings/{slug}/{job_id}", timeout=8)
            if r.ok:
                data = r.json()
                return data.get("descriptionPlain", "") or data.get("description", "")
        except Exception:
            pass
    # Ashby — no single-job endpoint; fetch all and match by id
    m = _ASH_URL.search(url)
    if m:
        slug, job_id = m.group(1), m.group(2)
        try:
            r = requests.get(
                f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
                timeout=8,
            )
            if r.ok:
                for j in r.json().get("jobs", []):
                    if j.get("id") == job_id or j.get("jobUrl", "").endswith(job_id):
                        return j.get("descriptionHtml", "")
        except Exception:
            pass
    return ""


def enrich_descriptions(jobs: list[dict]) -> list[dict]:
    """
    For jobs with no description, try to fetch from ATS using job_url_direct.
    LinkedIn/Indeed block scraping — but their listings often link to Greenhouse/Lever/Ashby.
    """
    missing = [j for j in jobs if not j.get("description", "").strip()]
    if not missing:
        return jobs
    log.info("enriching %d jobs with missing descriptions via ATS direct URLs…", len(missing))
    enriched_count = 0
    for job in missing:
        direct_url = job.get("url_direct", "") or job.get("url", "")
        desc = _fetch_description_from_ats_url(direct_url)
        if desc.strip():
            job["description"] = desc
            enriched_count += 1
            log.debug("ATS-enriched description for %r @ %r", job["title"], job["company"])
        time.sleep(0.3)
    log.info("ATS enriched %d / %d missing descriptions", enriched_count, len(missing))
    return jobs


# ── RemoteOK ──────────────────────────────────────────────────────────────────

def fetch_remoteok() -> list[dict]:
    """RemoteOK's public JSON API, filtered to the design tag. First array element is
    an API-terms object, not a job — skip rows without an id."""
    try:
        resp = requests.get(
            "https://remoteok.com/api",
            params={"tags": "design"},
            headers=_BROWSER_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        jobs = []
        for job in resp.json():
            if not job.get("id"):
                continue
            jobs.append(_normalize(
                title=job.get("position", ""),
                company=job.get("company", ""),
                location=job.get("location", "") or "Remote",
                description=job.get("description", ""),
                url=job.get("url", ""),
                source="remoteok",
                date_posted=job.get("date", ""),
            ))
        return jobs
    except Exception as exc:
        log.warning("remoteok error: %s", exc)
        return []


# ── Working Nomads ────────────────────────────────────────────────────────────

def fetch_working_nomads() -> list[dict]:
    """Working Nomads public JSON API, filtered client-side to the Design category."""
    try:
        resp = requests.get(
            "https://www.workingnomads.com/api/exposed_jobs/",
            headers=_BROWSER_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        jobs = []
        for job in resp.json():
            if job.get("category_name") != "Design":
                continue
            jobs.append(_normalize(
                title=job.get("title", ""),
                company=job.get("company_name", ""),
                location=job.get("location", "") or "Remote",
                description=job.get("description", ""),
                url=job.get("url", ""),
                source="workingnomads",
                date_posted=job.get("pub_date", ""),
            ))
        return jobs
    except Exception as exc:
        log.warning("workingnomads error: %s", exc)
        return []


# ── We Work Remotely (design category RSS) ───────────────────────────────────

def fetch_wwr_design() -> list[dict]:
    """We Work Remotely's Design-category RSS feed. Title format is 'Company: Position'."""
    try:
        resp = requests.get(
            "https://weworkremotely.com/categories/remote-design-jobs.rss",
            headers=_BROWSER_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        jobs = []
        for item in root.findall(".//item"):
            raw_title = (item.findtext("title") or "").strip()
            company, _, position = raw_title.partition(": ")
            if not position:
                company, position = "", raw_title
            jobs.append(_normalize(
                title=position.strip(),
                company=company.strip(),
                location=(item.findtext("region") or "").strip() or "Remote",
                description=item.findtext("description") or "",
                url=item.findtext("link") or "",
                source="weworkremotely",
                date_posted=item.findtext("pubDate") or "",
            ))
        return jobs
    except Exception as exc:
        log.warning("weworkremotely error: %s", exc)
        return []


# ── Simplify New-Grad Positions (GitHub) ──────────────────────────────────────

_SIMPLIFY_README = (
    "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/README.md"
)
_SIMPLIFY_ROW = re.compile(r"<tr>\s*(.*?)\s*</tr>", re.DOTALL)
_SIMPLIFY_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL)
_SIMPLIFY_HREF = re.compile(r'href="([^"]+)"')


def fetch_simplify_newgrad() -> list[dict]:
    """Simplify's New-Grad-Positions GitHub list — mostly SWE roles, but has occasional
    real UX/Product Designer entries. Pre-filtered to design titles here (not in filter.py)
    since the table has thousands of rows and most are irrelevant."""
    try:
        resp = requests.get(_SIMPLIFY_README, headers=_BROWSER_HEADERS, timeout=15)
        resp.raise_for_status()
        jobs = []
        for row in _SIMPLIFY_ROW.findall(resp.text):
            if "🔒" in row:  # application closed
                continue
            cells = _SIMPLIFY_CELL.findall(row)
            if len(cells) < 4:
                continue
            company_cell, title_cell, location_cell, apply_cell = cells[0], cells[1], cells[2], cells[3]
            title = _clean_html(title_cell)
            if not config.TITLE_REQUIRED.search(title):
                continue
            company = _clean_html(company_cell)
            location = _clean_html(location_cell)
            hrefs = _SIMPLIFY_HREF.findall(apply_cell) or _SIMPLIFY_HREF.findall(company_cell)
            url = hrefs[0] if hrefs else ""
            jobs.append(_normalize(
                title=title,
                company=company,
                location=location,
                description="",
                url=url,
                source="simplify/new-grad",
            ))
        return jobs
    except Exception as exc:
        log.warning("simplify new-grad error: %s", exc)
        return []


def _clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# ── Orchestrator ──────────────────────────────────────────────────────────────

def fetch_all() -> list[dict]:
    jobs: list[dict] = []

    log.info("fetching jobspy…")
    jobs.extend(fetch_jobspy())

    log.info("fetching adzuna…")
    jobs.extend(fetch_adzuna())

    log.info("fetching adzuna india (bengaluru)…")
    jobs.extend(fetch_adzuna_india())

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

    log.info("fetching remoteok (design)…")
    jobs.extend(fetch_remoteok())

    log.info("fetching working nomads (design)…")
    jobs.extend(fetch_working_nomads())

    log.info("fetching we work remotely (design)…")
    jobs.extend(fetch_wwr_design())

    log.info("fetching simplify new-grad list…")
    jobs.extend(fetch_simplify_newgrad())

    # Dedup within batch: by URL-based id first, then by content fingerprint.
    # Fingerprint catches same job appearing on multiple boards (LinkedIn + Greenhouse etc).
    seen_ids: set[str] = set()
    seen_fps: set[str] = set()
    unique: list[dict] = []
    for job in jobs:
        if job["id"] in seen_ids or job["fingerprint"] in seen_fps:
            continue
        seen_ids.add(job["id"])
        seen_fps.add(job["fingerprint"])
        unique.append(job)

    log.info("fetched %d unique jobs total (before cross-run dedup)", len(unique))

    # Enrich any jobs still missing descriptions (LinkedIn blocks JobSpy scraping).
    # Jina AI converts job URLs to readable text so experience filter can run properly.
    enrich_descriptions(unique)

    return unique
