from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from typing import Any

import httpx

from .base import BaseFeed, FeedItem


OSV_ENDPOINT = "https://api.osv.dev/v1/query"

ECOSYSTEM_MAP = {
    "npm": "npm",
    "pip": "PyPI",
    "pypi": "PyPI",
    "go": "Go",
    "gomod": "Go",
    "maven": "Maven",
    "nuget": "NuGet",
    "rubygems": "RubyGems",
    "ruby": "RubyGems",
    "crates": "crates.io",
    "crates.io": "crates.io",
}


@dataclass
class OSVSettings:
    packages: dict[str, list[str]]
    max_results: int
    timeout_seconds: int
    user_agent: str


class OSVFeed(BaseFeed):
    def __init__(self, settings: OSVSettings) -> None:
        self._settings = settings
        self._logger = logging.getLogger(__name__)

    async def fetch_recent(self, since: datetime | None = None) -> list[FeedItem]:
        start = since or (datetime.now(timezone.utc) - timedelta(days=1))
        items: list[FeedItem] = []
        headers = {"User-Agent": self._settings.user_agent}

        async with httpx.AsyncClient(timeout=self._settings.timeout_seconds) as client:
            for ecosystem, packages in self._settings.packages.items():
                internal_ecosystem = ecosystem.lower()
                osv_ecosystem = ECOSYSTEM_MAP.get(internal_ecosystem, ecosystem)
                for package in packages:
                    payload = {"package": {"name": package, "ecosystem": osv_ecosystem}}
                    response = await client.post(OSV_ENDPOINT, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                    for vuln in data.get("vulns", []):
                        if len(items) >= self._settings.max_results:
                            return items
                        item = _parse_vuln(vuln, package, start, internal_ecosystem)
                        if item:
                            items.append(item)
        return items


def _parse_vuln(
    vuln: dict[str, Any],
    package: str,
    since: datetime,
    ecosystem: str,
) -> FeedItem | None:
    vuln_id = vuln.get("id")
    if not vuln_id:
        return None
    published = _parse_datetime(vuln.get("published"))
    if published < since:
        return None
    summary = vuln.get("summary") or ""
    details = vuln.get("details") or summary
    url = _first_reference(vuln.get("references", []))
    return FeedItem(
        id=f"osv:{vuln_id}",
        source="osv",
        title=f"{vuln_id}: {summary}" if summary else vuln_id,
        description=details,
        url=url,
        published=published,
        severity=None,
        cvss_score=None,
        affected_packages=[package],
        raw_data=vuln,
        ecosystems=[ecosystem],
    )


def _first_reference(references: list[dict[str, Any]]) -> str:
    for ref in references:
        url = ref.get("url")
        if url:
            return url
    return ""


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return datetime.now(timezone.utc)
