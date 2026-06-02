"""
E-Verify employer lookup using the public search endpoint.
Caches results in-memory for the run lifetime. Returns:
  True  → confirmed E-Verify participant
  False → found but not enrolled (rare — search only returns enrolled)
  None  → lookup failed or no match
"""

import logging
from typing import Optional

import requests
from rapidfuzz import process as fuzz_process

log = logging.getLogger(__name__)

# In-memory cache: normalized_name → True|False
_cache: dict[str, bool] = {}

_SEARCH_URL = (
    "https://www.e-verify.gov/employers/employer-search"
    "?searchCriteria={query}&searchType=companyName"
)
_API_URL = "https://www.e-verify.gov/api/employer-search"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; job-alert-bot/1.0)",
    "Accept": "application/json",
}


def _query_everify(company_name: str) -> list[str]:
    """Return list of employer names returned by E-Verify search."""
    try:
        resp = requests.get(
            _API_URL,
            params={"searchCriteria": company_name, "searchType": "companyName"},
            headers=_HEADERS,
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            # Response is typically {"employers": [{"employerName": "..."}]}
            employers = data.get("employers", data if isinstance(data, list) else [])
            return [e.get("employerName", "") for e in employers if e.get("employerName")]
        # Some versions return results at root level
        return []
    except Exception as exc:
        log.debug("e-verify API error for %r: %s", company_name, exc)
        return []


def lookup(company_name: str) -> Optional[bool]:
    """Check if company participates in E-Verify."""
    key = company_name.lower().strip()

    # Check cache with fuzzy match against known keys
    if _cache:
        match = fuzz_process.extractOne(key, _cache.keys(), score_cutoff=85)
        if match:
            matched_key = match[0]
            log.debug("e-verify cache hit: %r → %r", key, matched_key)
            return _cache[matched_key]

    employers = _query_everify(company_name)
    if not employers:
        # Try shorter version of name (first word) as fallback
        first_word = company_name.split()[0] if company_name.split() else company_name
        if first_word != company_name:
            employers = _query_everify(first_word)

    if not employers:
        log.debug("e-verify: no results for %r", company_name)
        return None

    # Fuzzy match the company name against returned employer names
    match = fuzz_process.extractOne(key, [e.lower() for e in employers], score_cutoff=75)
    enrolled = match is not None

    _cache[key] = enrolled
    log.debug("e-verify: %r → enrolled=%s (best match: %s)", key, enrolled, match)
    return enrolled


def enrolled_label(result: Optional[bool]) -> str:
    if result is True:
        return "Yes"
    if result is False:
        return "No"
    return "Unknown"
