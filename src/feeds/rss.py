from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import asyncio
from email.utils import parsedate_to_datetime
import logging
from typing import Any
import xml.etree.ElementTree as ET

import httpx

from .base import BaseFeed, FeedItem


@dataclass
class RSSSource:
    name: str
    url: str


@dataclass
class RSSSettings:
    sources: list[RSSSource]
    timeout_seconds: int
    user_agent: str


class RSSFeed(BaseFeed):
    def __init__(self, settings: RSSSettings) -> None:
        self._settings = settings
        self._logger = logging.getLogger(__name__)

    async def fetch_recent(self, since: datetime | None = None) -> list[FeedItem]:
        if not self._settings.sources:
            return []
        start = since or (datetime.now(timezone.utc) - timedelta(days=1))
        headers = {"User-Agent": self._settings.user_agent}

        async with httpx.AsyncClient(timeout=self._settings.timeout_seconds) as client:
            tasks = [
                _fetch_source(client, source, headers, start) for source in self._settings.sources
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        items: list[FeedItem] = []
        for result in results:
            if isinstance(result, Exception):
                self._logger.warning("RSS fetch failed: %s", result)
                continue
            items.extend(result)
        return items


async def _fetch_source(
    client: httpx.AsyncClient,
    source: RSSSource,
    headers: dict[str, str],
    since: datetime,
) -> list[FeedItem]:
    response = await client.get(source.url, headers=headers)
    response.raise_for_status()
    return _parse_feed(source, response.text, since)


def _parse_feed(source: RSSSource, payload: str, since: datetime) -> list[FeedItem]:
    root = ET.fromstring(payload)
    tag = _strip_namespace(root.tag)
    if tag == "rss":
        return _parse_rss_channel(source, root, since)
    if tag == "feed":
        return _parse_atom_feed(source, root, since)
    return []


def _parse_rss_channel(source: RSSSource, root: ET.Element, since: datetime) -> list[FeedItem]:
    channel = root.find("channel")
    if channel is None:
        return []
    items: list[FeedItem] = []
    for item in channel.findall("item"):
        title = _text(item, "title") or source.name
        description = _text(item, "description") or ""
        link = _text(item, "link") or ""
        guid = _text(item, "guid") or link or title
        published = _parse_pubdate(_text(item, "pubDate"))
        if published < since:
            continue
        items.append(
            FeedItem(
                id=f"rss:{source.name}:{guid}",
                source=source.name.lower(),
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
    return items


def _parse_atom_feed(source: RSSSource, root: ET.Element, since: datetime) -> list[FeedItem]:
    items: list[FeedItem] = []
    for entry in root.findall("{*}entry"):
        title = _text(entry, "title") or source.name
        description = _text(entry, "summary") or _text(entry, "content") or ""
        link = _atom_link(entry)
        entry_id = _text(entry, "id") or link or title
        published = _parse_pubdate(_text(entry, "updated") or _text(entry, "published"))
        if published < since:
            continue
        items.append(
            FeedItem(
                id=f"rss:{source.name}:{entry_id}",
                source=source.name.lower(),
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
    return items


def _atom_link(entry: ET.Element) -> str:
    for link in entry.findall("{*}link"):
        href = link.attrib.get("href")
        if href:
            return href
    return ""


def _parse_pubdate(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)


def _text(node: ET.Element, tag: str) -> str | None:
    child = node.find(tag)
    if child is None:
        child = node.find(f\"{{*}}{tag}\")
    if child is None or child.text is None:
        return None
    return child.text.strip()


def _strip_namespace(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag
