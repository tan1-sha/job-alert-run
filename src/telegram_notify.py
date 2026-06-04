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
    url = job["url"] or "No link"

    lines = [
        f"*{_e(job['title'])}*, {_e(job['company'])}",
        _e(location),
        url,
    ]

    # Surface review flags so candidate knows to verify manually
    if bucket == "REVIEW" or "verify" in reason.lower() or "check" in reason.lower():
        lines.append(f"Note: {_e(reason)}")

    text = "\n".join(lines)

    try:
        resp = requests.post(
            _api_url(),
            json={
                "chat_id": config.TELEGRAM_CHAT,
                "text": text,
                "parse_mode": "MarkdownV2",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        resp.raise_for_status()
        log.info("telegram [%s]: %r @ %r", bucket, job["title"], job["company"])
    except Exception as exc:
        log.error("telegram: failed for %r: %s", job["title"], exc)


def _e(text: str) -> str:
    """Escape special chars for Telegram MarkdownV2."""
    special = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in str(text))
