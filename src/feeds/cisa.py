from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

import httpx

from .base import BaseFeed, FeedItem


CISA_ENDPOINT = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"


@dataclass
class CISASettings:
    timeout_seconds: int
    user_agent: str


class CISAFeed(BaseFeed):
    def __init__(self, settings: CISASettings) -> None:
        self._settings = settings
        self._logger = logging.getLogger(__name__)

    async def fetch_recent(self, since: datetime | None = None) -> list[FeedItem]:
        start = since or (datetime.now(timezone.utc) - timedelta(days=1))
        headers = {"User-Agent": self._settings.user_agent}

        async with httpx.AsyncClient(timeout=self._settings.timeout_seconds) as client:
            response = await client.get(CISA_ENDPOINT, headers=headers)
            response.raise_for_status()
            payload = response.json()

        return _parse_items(payload, start)


def _parse_items(payload: dict[str, Any], since: datetime) -> list[FeedItem]:
    results: list[FeedItem] = []
    vulnerabilities = payload.get("vulnerabilities", [])
    for entry in vulnerabilities:
        cve_id = entry.get("cveID")
        if not cve_id:
            continue
        published = _parse_date(entry.get("dateAdded"))
        if published < since:
            continue
        title = entry.get("vulnerabilityName") or cve_id
        description = entry.get("shortDescription") or ""
        url = f"https://nvd.nist.gov/vuln/detail/{cve_id}"
        results.append(
            FeedItem(
                id=f"cisa:{cve_id}",
                source="cisa",
                title=f"{cve_id}: {title}",
                description=description,
                url=url,
                published=published,
                severity=None,
                cvss_score=None,
                affected_packages=[],
                raw_data=entry,
            )
        )
    return results


def _parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)
