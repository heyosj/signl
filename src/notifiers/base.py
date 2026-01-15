from __future__ import annotations

from abc import ABC, abstractmethod

from ..feeds.base import FeedItem


class BaseNotifier(ABC):
    @abstractmethod
    async def send(self, item: FeedItem, reasons: list[str]) -> bool:
        """Send notification. Returns True if successful."""
        raise NotImplementedError
