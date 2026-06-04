import logging

import requests

from src import config

log = logging.getLogger(__name__)


def _api_url() -> str:
    return f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"


def send_strong(job: dict, reason: str) -> None:
    _send(job, bucket="STRONG", reason=reason)


def send_review(job: dict, reason: str) -> None:
    _send(job, bucket="REVIEW", reason=reason)


def _send(job: dict, bucket: str, reason: str) -> None:
    location = job["location"] or "Location not listed"
    url      = job["url"] or "No link"

    lines = [
        f"<b>{_h(job['title'])}</b>, {_h(job['company'])}",
        _h(location),
        url,
    ]

    # Only add Note when something needs manual review
    _clean_prefixes = ("passed all filters", "priority company")
    needs_note = bucket == "REVIEW" or not any(
        reason.lower().startswith(p) for p in _clean_prefixes
    )
    if needs_note:
        lines.append(f"Note: {_h(reason)}")

    try:
        resp = requests.post(
            _api_url(),
            json={
                "chat_id": config.TELEGRAM_CHAT,
                "text": "\n".join(lines),
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        resp.raise_for_status()
        log.info("telegram [%s]: %r @ %r", bucket, job["title"], job["company"])
    except Exception as exc:
        log.error("telegram: failed for %r: %s", job["title"], exc)


def _h(text: str) -> str:
    """Escape HTML special chars for Telegram HTML parse mode."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
