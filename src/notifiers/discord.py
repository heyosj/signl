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
    "critical": 0xE74C3C,
    "high": 0xE67E22,
    "medium": 0xF1C40F,
    "low": 0x95A5A6,
}


@dataclass
class DiscordSettings:
    webhook_url: str
    timeout_seconds: int
    user_agent: str


class DiscordNotifier(BaseNotifier):
    def __init__(self, settings: DiscordSettings) -> None:
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
                    self._logger.warning("Discord rate limit hit, sleeping %.2fs", retry_after)
                    time.sleep(retry_after)
                    continue
                if 200 <= response.status_code < 300:
                    return True
                self._logger.error("Discord webhook failed with status %s", response.status_code)
            return False


def _build_payload(item: FeedItem, reasons: list[str]) -> dict[str, Any]:
    severity = (item.severity or "").lower()
    color = SEVERITY_COLORS.get(severity, SEVERITY_COLORS["low"])
    description = item.description
    if len(description) > 400:
        description = description[:397] + "..."

    fields = [
        {
            "name": "Severity",
            "value": _format_severity(item.severity, item.cvss_score),
            "inline": True,
        },
        {"name": "Source", "value": item.source.upper(), "inline": True},
    ]

    if item.affected_packages:
        packages = ", ".join(item.affected_packages[:10])
        fields.append({"name": "Affected", "value": packages, "inline": False})

    if reasons:
        reason_text = "\n".join(reasons[:5])
        fields.append({"name": "Why you're seeing this", "value": reason_text, "inline": False})

    timestamp = item.published.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "embeds": [
            {
                "title": item.title,
                "description": description,
                "url": item.url,
                "color": color,
                "fields": fields,
                "timestamp": timestamp,
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
