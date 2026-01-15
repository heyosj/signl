from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone
import logging
import time
from typing import Any

import httpx

from .base import BaseNotifier
from .message import NotificationMessage, NotificationMetadata


SEVERITY_COLORS = {
    "p0": "#E74C3C",
    "p1": "#E67E22",
    "p2": "#F1C40F",
    "p3": "#95A5A6",
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

    async def send(self, message: NotificationMessage, metadata: NotificationMetadata) -> bool:
        payload = _build_payload(message, metadata)
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


def _build_payload(message: NotificationMessage, metadata: NotificationMetadata) -> dict[str, Any]:
    severity_key = message.priority.lower()
    color = SEVERITY_COLORS.get(severity_key, SEVERITY_COLORS["low"])
    description = message.summary
    if len(description) > 300:
        description = description[:297] + "..."

    reason_text = "\n".join(metadata.reasons[:5]) if metadata.reasons else "Matched your stack"
    rationale_text = "\n".join(metadata.rationale[:2]) if metadata.rationale else "Scored with defaults"
    timestamp = message.published.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "attachments": [
            {
                "color": color,
                "title": message.title,
                "title_link": message.url,
                "text": description,
                "fields": [
                    {"title": "Priority", "value": f"{message.priority} ({message.score})", "short": True},
                    {"title": "Source", "value": message.source.upper(), "short": True},
                    {"title": "Why you're seeing this", "value": reason_text, "short": False},
                    {"title": "Scoring", "value": rationale_text, "short": False},
                ],
                "footer": "signl",
                "ts": int(message.published.timestamp()),
            }
        ]
    }


def _retry_after(response: httpx.Response) -> float:
    value = response.headers.get("Retry-After")
    if not value:
        return 1.0
    try:
        return float(value)
    except ValueError:
        return 1.0
