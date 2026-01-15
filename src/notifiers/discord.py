from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone
import logging
import asyncio
import time
from typing import Any

import httpx

from .base import BaseNotifier
from .message import NotificationMessage, NotificationMetadata


SEVERITY_COLORS = {
    "p0": 0xE74C3C,
    "p1": 0xE67E22,
    "p2": 0xF1C40F,
    "p3": 0x95A5A6,
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
        self._last_sent_at = 0.0

    async def send(self, message: NotificationMessage, metadata: NotificationMetadata) -> bool:
        await self._throttle()
        payload = _build_payload(message, metadata)
        headers = {"User-Agent": self._settings.user_agent}

        async with httpx.AsyncClient(timeout=self._settings.timeout_seconds) as client:
            for attempt in range(3):
                response = await client.post(self._settings.webhook_url, json=payload, headers=headers)
                if response.status_code == 429:
                    retry_after = _retry_after(response)
                    self._logger.warning("Discord rate limit hit, sleeping %.2fs", retry_after)
                    await asyncio.sleep(retry_after)
                    continue
                if 200 <= response.status_code < 300:
                    return True
                self._logger.error("Discord webhook failed with status %s", response.status_code)
            return False

    async def _throttle(self) -> None:
        min_interval = 0.5
        now = time.monotonic()
        elapsed = now - self._last_sent_at
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_sent_at = time.monotonic()


def _build_payload(message: NotificationMessage, metadata: NotificationMetadata) -> dict[str, Any]:
    severity = message.priority.lower()
    color = SEVERITY_COLORS.get(severity, SEVERITY_COLORS["p3"])
    description = message.summary
    if len(description) > 400:
        description = description[:397] + "..."

    fields = [
        {
            "name": "Priority",
            "value": f"{message.priority} ({message.score})",
            "inline": True,
        },
        {"name": "Source", "value": message.source.upper(), "inline": True},
    ]

    if message.affected.get("packages"):
        packages = ", ".join(message.affected.get("packages", [])[:10])
        fields.append({"name": "Affected", "value": packages, "inline": False})

    if metadata.reasons:
        reason_text = "\n".join(metadata.reasons[:5])
        fields.append({"name": "Why you're seeing this", "value": reason_text, "inline": False})

    if metadata.rationale:
        fields.append({"name": "Scoring", "value": "\n".join(metadata.rationale[:2]), "inline": False})

    timestamp = message.published.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    return {
        "embeds": [
            {
                "title": message.title,
                "description": description,
                "url": message.url,
                "color": color,
                "fields": fields,
                "timestamp": timestamp,
            }
        ]
    }


def _retry_after(response: httpx.Response) -> float:
    value = response.headers.get("Retry-After") or response.headers.get("X-RateLimit-Reset-After")
    if not value:
        try:
            data = response.json()
        except ValueError:
            return 1.0
        retry_after = data.get("retry_after")
        if retry_after is None:
            return 1.0
        try:
            return float(retry_after)
        except (TypeError, ValueError):
            return 1.0
    try:
        return float(value)
    except ValueError:
        return 1.0
