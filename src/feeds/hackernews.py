from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

import httpx

from .base import BaseFeed, FeedItem


HN_ENDPOINT = "https://hn.algolia.com/api/v1/search_by_date"


@dataclass
class HackerNewsSettings:
    terms: list[str]
    max_results: int
    timeout_seconds: int
    user_agent: str


class HackerNewsFeed(BaseFeed):
    def __init__(self, settings: HackerNewsSettings) -> None:
        self._settings = settings
        self._logger = logging.getLogger(__name__)

    async def fetch_recent(self, since: datetime | None = None) -> list[FeedItem]:
        if not self._settings.terms:
            return []
        start = since or (datetime.now(timezone.utc) - timedelta(days=1))
        since_epoch = int(start.timestamp())
        headers = {"User-Agent": self._settings.user_agent}
        results: list[FeedItem] = []
        seen: set[str] = set()

        async with httpx.AsyncClient(timeout=self._settings.timeout_seconds) as client:
            for term in self._settings.terms:
                params = {
                    "query": term,
                    "tags": "story",
                    "numericFilters": f"created_at_i>{since_epoch}",
                    "hitsPerPage": min(self._settings.max_results, 20),
                }
                response = await client.get(HN_ENDPOINT, params=params, headers=headers)
                response.raise_for_status()
                payload = response.json()
                for hit in payload.get("hits", []):
                    item = _parse_hit(hit)
                    if not item:
                        continue
                    if item.id in seen:
                        continue
                    seen.add(item.id)
                    results.append(item)
                    if len(results) >= self._settings.max_results:
                        return results

        return results


def _parse_hit(hit: dict[str, Any]) -> FeedItem | None:
    object_id = hit.get("objectID")
    if not object_id:
        return None
    title = hit.get("title") or "Hacker News"
    url = hit.get("url") or f"https://news.ycombinator.com/item?id={object_id}"
    created_at = hit.get("created_at")
    published = _parse_datetime(created_at)
    description = hit.get("story_text") or hit.get("title") or ""
    return FeedItem(
        id=f"hn:{object_id}",
        source="hackernews",
        title=title,
        description=description,
        url=url,
        published=published,
        severity=None,
        cvss_score=None,
        affected_packages=[],
        raw_data=hit,
    )


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.now(timezone.utc)
