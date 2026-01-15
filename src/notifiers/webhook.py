from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone
import logging
from typing import Any

import httpx

from .base import BaseNotifier
from .message import NotificationMessage, NotificationMetadata


@dataclass
class WebhookSettings:
    url: str
    headers: dict[str, str]
    timeout_seconds: int
    user_agent: str


class WebhookNotifier(BaseNotifier):
    def __init__(self, settings: WebhookSettings) -> None:
        self._settings = settings
        self._logger = logging.getLogger(__name__)

    async def send(self, message: NotificationMessage, metadata: NotificationMetadata) -> bool:
        payload = _build_payload(message, metadata)
        headers = {"User-Agent": self._settings.user_agent}
        headers.update(self._settings.headers)

        async with httpx.AsyncClient(timeout=self._settings.timeout_seconds) as client:
            response = await client.post(self._settings.url, json=payload, headers=headers)
            if 200 <= response.status_code < 300:
                return True
            self._logger.error("Webhook failed with status %s", response.status_code)
            return False


def _build_payload(message: NotificationMessage, metadata: NotificationMetadata) -> dict[str, Any]:
    published = message.published.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "title": message.title,
        "summary": message.summary,
        "priority": message.priority,
        "score": message.score,
        "url": message.url,
        "source": message.source,
        "published": published,
        "affected": message.affected,
        "tags": message.tags,
        "reasons": metadata.reasons,
        "rationale": metadata.rationale,
    }
