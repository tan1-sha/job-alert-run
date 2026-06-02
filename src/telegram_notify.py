import logging

import requests

from src import config

log = logging.getLogger(__name__)


def _api_url() -> str:
    return f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"


def send_strong(job: dict, reason: str) -> None:
    lines = [
        f"🔥 *STRONG MATCH*",
        f"*{_escape(job['title'])}*",
        f"🏢 {_escape(job['company'])}",
        f"📍 {_escape(job['location'] or 'Not specified')}",
        f"📌 {_escape(reason)}",
        f"[View Job]({job['url']})",
    ]
    text = "\n".join(lines)

    try:
        resp = requests.post(
            _api_url(),
            json={
                "chat_id": config.TELEGRAM_CHAT,
                "text": text,
                "parse_mode": "MarkdownV2",
                "disable_web_page_preview": False,
            },
            timeout=10,
        )
        resp.raise_for_status()
        log.info("telegram: sent alert for %r @ %r", job["title"], job["company"])
    except Exception as exc:
        log.error("telegram: failed for %r: %s", job["title"], exc)


def _escape(text: str) -> str:
    """Escape special chars for Telegram MarkdownV2."""
    special = r"\_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in str(text))
