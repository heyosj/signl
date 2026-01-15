from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

import httpx

from .base import BaseFeed, FeedItem


GITHUB_ADVISORIES_ENDPOINT = "https://api.github.com/advisories"


@dataclass
class GitHubSettings:
    ecosystems: list[str]
    max_results: int
    timeout_seconds: int
    user_agent: str


class GitHubFeed(BaseFeed):
    def __init__(self, settings: GitHubSettings) -> None:
        self._settings = settings
        self._logger = logging.getLogger(__name__)

    async def fetch_recent(self, since: datetime | None = None) -> list[FeedItem]:
        start = since or (datetime.now(timezone.utc) - timedelta(days=1))
        items: list[FeedItem] = []

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": self._settings.user_agent,
        }

        page = 1
        per_page = min(self._settings.max_results, 100)

        async with httpx.AsyncClient(timeout=self._settings.timeout_seconds) as client:
            while True:
                params: dict[str, Any] = {
                    "per_page": per_page,
                    "page": page,
                }
                if len(self._settings.ecosystems) == 1:
                    params["ecosystem"] = self._settings.ecosystems[0]
                if since:
                    params["since"] = _to_iso(start)

                response = await client.get(GITHUB_ADVISORIES_ENDPOINT, headers=headers, params=params)
                response.raise_for_status()
                payload = response.json()
                if not payload:
                    break

                items.extend(_parse_items(payload))
                if len(payload) < per_page:
                    break
                page += 1

        return items


def _parse_items(entries: list[dict[str, Any]]) -> list[FeedItem]:
    results: list[FeedItem] = []
    for entry in entries:
        ghsa_id = entry.get("ghsa_id")
        if not ghsa_id:
            continue
        title = entry.get("summary") or ghsa_id
        description = entry.get("description") or entry.get("summary") or ""
        severity = _normalize_severity(entry.get("severity"))
        published = _parse_datetime(entry.get("published_at"))
        url = entry.get("html_url") or ""
        affected = _extract_packages(entry.get("vulnerabilities", []))
        results.append(
            FeedItem(
                id=ghsa_id,
                source="github",
                title=f"{ghsa_id}: {title}",
                description=description,
                url=url,
                published=published,
                severity=severity,
                cvss_score=None,
                affected_packages=affected,
                raw_data=entry,
            )
        )
    return results


def _extract_packages(vulnerabilities: list[dict[str, Any]]) -> list[str]:
    packages: set[str] = set()
    for vuln in vulnerabilities:
        package = vuln.get("package", {})
        name = package.get("name")
        if name:
            packages.add(name)
    return sorted(packages)


def _normalize_severity(value: str | None) -> str | None:
    if not value:
        return None
    return value.lower()


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
