from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone
import logging
import time
from typing import Any

import httpx

from .base import BaseNotifier
from ..feeds.base import FeedItem


SEVERITY_COLORS = {
    "critical": "#E74C3C",
    "high": "#E67E22",
    "medium": "#F1C40F",
    "low": "#95A5A6",
}


@dataclass
class SlackSettings:
    webhook_url: str
    timeout_seconds: int
    user_agent: str


class SlackNotifier(BaseNotifier):
    def __init__(self, settings: SlackSettings) -> None:
        self._settings = settings
        self._logger = logging.getLogger(__name__)

    async def send(self, item: FeedItem, reasons: list[str]) -> bool:
        payload = _build_payload(item, reasons)
        headers = {"User-Agent": self._settings.user_agent}

        async with httpx.AsyncClient(timeout=self._settings.timeout_seconds) as client:
            for attempt in range(3):
                response = await client.post(self._settings.webhook_url, json=payload, headers=headers)
                if response.status_code == 429:
                    retry_after = _retry_after(response)
                    self._logger.warning("Slack rate limit hit, sleeping %.2fs", retry_after)
                    time.sleep(retry_after)
                    continue
                if 200 <= response.status_code < 300:
                    return True
                self._logger.error("Slack webhook failed with status %s", response.status_code)
            return False


def _build_payload(item: FeedItem, reasons: list[str]) -> dict[str, Any]:
    severity = (item.severity or "").lower()
    color = SEVERITY_COLORS.get(severity, SEVERITY_COLORS["low"])
    description = item.description
    if len(description) > 300:
        description = description[:297] + "..."

    reason_text = "\n".join(reasons[:5]) if reasons else "Matched your stack"
    timestamp = item.published.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "attachments": [
            {
                "color": color,
                "title": item.title,
                "title_link": item.url,
                "text": description,
                "fields": [
                    {"title": "Severity", "value": _format_severity(item.severity, item.cvss_score), "short": True},
                    {"title": "Source", "value": item.source.upper(), "short": True},
                    {"title": "Why you're seeing this", "value": reason_text, "short": False},
                ],
                "footer": "signl",
                "ts": int(item.published.timestamp()),
            }
        ]
    }


def _format_severity(severity: str | None, score: float | None) -> str:
    if not severity and score is None:
        return "Unknown"
    if score is None:
        return severity.title() if severity else "Unknown"
    if severity:
        return f"{severity.title()} ({score:.1f})"
    return f"{score:.1f}"


def _retry_after(response: httpx.Response) -> float:
    value = response.headers.get("Retry-After")
    if not value:
        return 1.0
    try:
        return float(value)
    except ValueError:
        return 1.0
