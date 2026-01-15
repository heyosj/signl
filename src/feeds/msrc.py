from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import logging
from typing import Any
import xml.etree.ElementTree as ET

import httpx

from .base import BaseFeed, FeedItem


MSRC_RSS_ENDPOINT = "https://api.msrc.microsoft.com/update-guide/rss"


@dataclass
class MSRCSettings:
    timeout_seconds: int
    user_agent: str


class MSRCFeed(BaseFeed):
    def __init__(self, settings: MSRCSettings) -> None:
        self._settings = settings
        self._logger = logging.getLogger(__name__)

    async def fetch_recent(self, since: datetime | None = None) -> list[FeedItem]:
        start = since or (datetime.now(timezone.utc) - timedelta(days=1))
        headers = {"User-Agent": self._settings.user_agent}

        async with httpx.AsyncClient(timeout=self._settings.timeout_seconds) as client:
            response = await client.get(MSRC_RSS_ENDPOINT, headers=headers)
            response.raise_for_status()

        return _parse_rss(response.text, start)


def _parse_rss(payload: str, since: datetime) -> list[FeedItem]:
    results: list[FeedItem] = []
    root = ET.fromstring(payload)
    for item in root.findall(".//item"):
        guid = _text(item, "guid") or _text(item, "link")
        if not guid:
            continue
        title = _text(item, "title") or guid
        description = _text(item, "description") or ""
        link = _text(item, "link") or ""
        published = _parse_pubdate(_text(item, "pubDate"))
        if published < since:
            continue
        results.append(
            FeedItem(
                id=f"msrc:{guid}",
                source="msrc",
                title=title,
                description=description,
                url=link,
                published=published,
                severity=None,
                cvss_score=None,
                affected_packages=[],
                raw_data={},
            )
        )
    return results


def _text(node: ET.Element, tag: str) -> str | None:
    child = node.find(tag)
    if child is None or child.text is None:
        return None
    return child.text.strip()


def _parse_pubdate(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = parsedate_to_datetime(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
