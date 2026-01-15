from __future__ import annotations

from abc import ABC, abstractmethod

from .message import NotificationMessage, NotificationMetadata


class BaseNotifier(ABC):
    @abstractmethod
    async def send(self, message: NotificationMessage, metadata: NotificationMetadata) -> bool:
        """Send notification. Returns True if successful."""
        raise NotImplementedError
