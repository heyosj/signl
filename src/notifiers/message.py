from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class NotificationMessage:
    title: str
    summary: str
    priority: str
    score: int
    url: str
    source: str
    published: datetime
    affected: dict[str, list[str]] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


@dataclass
class NotificationMetadata:
    reasons: list[str] = field(default_factory=list)
    rationale: list[str] = field(default_factory=list)
