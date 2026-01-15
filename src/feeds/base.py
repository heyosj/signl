from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class FeedItem:
    id: str
    source: str
    title: str
    description: str
    url: str
    published: datetime
    severity: str | None
    cvss_score: float | None
    affected_packages: list[str]
    raw_data: dict
    ecosystems: list[str] = field(default_factory=list)
    affected_services: list[str] = field(default_factory=list)
    affected_cloud: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


class BaseFeed(ABC):
    @abstractmethod
    async def fetch_recent(self, since: datetime | None = None) -> list[FeedItem]:
        """Fetch items published since the given datetime. If None, fetch last 24 hours."""
        raise NotImplementedError
