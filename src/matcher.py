from __future__ import annotations

import re
from typing import Iterable

from .feeds.base import FeedItem
from .config import StackConfig


_SHORT_TOKEN = re.compile(r"\b{}\b")


def _contains_token(text: str, token: str) -> bool:
    token = token.strip()
    if not token:
        return False
    if len(token) <= 3:
        pattern = _SHORT_TOKEN.pattern.format(re.escape(token))
        return re.search(pattern, text) is not None
    return token in text


def _lower_set(values: Iterable[str]) -> set[str]:
    return {value.lower() for value in values if value}


def calculate_relevance(item: FeedItem, config: StackConfig) -> tuple[bool, list[str]]:
    """
    Returns (is_relevant, list of reasons why it matched).

    Matching priority:
    1. Direct package name match (highest confidence)
    2. Service name match
    3. Keyword match
    4. Language match (only if specific to that language)
    5. Cloud provider match (only if specific service mentioned)
    """
    reasons: list[str] = []
    text = f"{item.title} {item.description}".lower()

    affected = _lower_set(item.affected_packages or [])
    for ecosystem, packages in config.packages.items():
        for pkg in packages:
            if pkg.lower() in affected:
                reasons.append(f"Direct package match: {pkg}")

    for ecosystem, packages in config.packages.items():
        for pkg in packages:
            token = pkg.lower()
            if _contains_token(text, token):
                reasons.append(f"Package mentioned: {pkg}")

    for service in config.services:
        token = service.lower()
        if _contains_token(text, token):
            reasons.append(f"Service match: {service}")

    for keyword in config.keywords:
        token = keyword.lower()
        if _contains_token(text, token):
            reasons.append(f"Keyword match: {keyword}")

    reasons = sorted(set(reasons))
    return (len(reasons) > 0, reasons)
