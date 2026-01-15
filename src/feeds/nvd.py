from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
import asyncio
from typing import Any

import httpx

from .base import BaseFeed, FeedItem


NVD_ENDPOINT = "https://services.nvd.nist.gov/rest/json/cves/2.0"


@dataclass
class NVDSettings:
    max_results: int
    timeout_seconds: int
    user_agent: str


class NVDFeed(BaseFeed):
    def __init__(self, settings: NVDSettings) -> None:
        self._settings = settings
        self._logger = logging.getLogger(__name__)

    async def fetch_recent(self, since: datetime | None = None) -> list[FeedItem]:
        start = since or (datetime.now(timezone.utc) - timedelta(days=1))
        end = datetime.now(timezone.utc)
        items: list[FeedItem] = []
        start_index = 0
        total_results = None

        headers = {"User-Agent": self._settings.user_agent}

        async with httpx.AsyncClient(timeout=self._settings.timeout_seconds) as client:
            while total_results is None or start_index < total_results:
                params = {
                    "pubStartDate": _to_iso(start),
                    "pubEndDate": _to_iso(end),
                    "resultsPerPage": self._settings.max_results,
                    "startIndex": start_index,
                }
                response = await client.get(NVD_ENDPOINT, headers=headers, params=params)
                response.raise_for_status()
                payload = response.json()
                total_results = int(payload.get("totalResults", 0))
                vulnerabilities = payload.get("vulnerabilities", [])
                items.extend(_parse_items(vulnerabilities))
                start_index += self._settings.max_results
                if start_index < total_results:
                    await asyncio.sleep(1)

        return items


def _parse_items(vulnerabilities: list[dict[str, Any]]) -> list[FeedItem]:
    results: list[FeedItem] = []
    for entry in vulnerabilities:
        cve = entry.get("cve", {})
        cve_id = cve.get("id")
        if not cve_id:
            continue
        published = _parse_datetime(cve.get("published"))
        description = _english_description(cve.get("descriptions", []))
        title = f"{cve_id}: {description.split('.', 1)[0]}" if description else cve_id
        cvss_score, severity = _cvss_v31(cve.get("metrics", {}))
        url = f"https://nvd.nist.gov/vuln/detail/{cve_id}"
        affected = _extract_cpes(cve.get("configurations", []))
        results.append(
            FeedItem(
                id=cve_id,
                source="nvd",
                title=title,
                description=description,
                url=url,
                published=published,
                severity=severity,
                cvss_score=cvss_score,
                affected_packages=affected,
                raw_data=cve,
            )
        )
    return results


def _english_description(descriptions: list[dict[str, Any]]) -> str:
    for desc in descriptions:
        if desc.get("lang") == "en":
            return desc.get("value", "")
    return ""


def _cvss_v31(metrics: dict[str, Any]) -> tuple[float | None, str | None]:
    entries = metrics.get("cvssMetricV31") or metrics.get("cvssMetricV30")
    if not entries:
        return None, None
    metric = entries[0]
    cvss = metric.get("cvssData", {})
    score = cvss.get("baseScore")
    severity = metric.get("baseSeverity")
    if isinstance(severity, str):
        severity = severity.lower()
    return score, severity


def _extract_cpes(configurations: list[dict[str, Any]]) -> list[str]:
    packages: set[str] = set()
    for config in configurations:
        nodes = config.get("nodes", [])
        for node in nodes:
            for match in node.get("cpeMatch", []) or []:
                criteria = match.get("criteria")
                if not criteria:
                    continue
                parts = criteria.split(":")
                if len(parts) >= 5:
                    packages.add(parts[4])
    return sorted(packages)


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
