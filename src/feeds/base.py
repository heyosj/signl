from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
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


class BaseFeed(ABC):
    @abstractmethod
    async def fetch_recent(self, since: datetime | None = None) -> list[FeedItem]:
        """Fetch items published since the given datetime. If None, fetch last 24 hours."""
        raise NotImplementedError
