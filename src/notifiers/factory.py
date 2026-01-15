from __future__ import annotations

import logging
from typing import Any

from .base import BaseNotifier
from .discord import DiscordNotifier, DiscordSettings
from .message import NotificationMessage, NotificationMetadata
from .slack import SlackNotifier, SlackSettings
from .webhook import WebhookNotifier, WebhookSettings
from ..config import Config
from ..feeds.base import FeedItem
from ..matcher import MatchResult
from ..scoring import AlertScore


def build_notifiers(config: Config) -> list[BaseNotifier]:
    logger = logging.getLogger(__name__)
    notifiers: list[BaseNotifier] = []
    if config.notifications.used_legacy:
        logger.warning("Using legacy notifications.* config; migrate to notify list.")

    for target in config.notifications.targets:
        notifier = _build_target(target.type, target.settings, config)
        if notifier:
            notifiers.append(notifier)
    return notifiers


def _build_target(target_type: str, settings: dict[str, Any], config: Config) -> BaseNotifier | None:
    normalized = target_type.lower()
    if normalized == "slack":
        webhook = _normalize_url(settings.get("webhook_url"))
        if not webhook:
            return None
        return SlackNotifier(
            SlackSettings(
                webhook_url=webhook,
                timeout_seconds=config.settings.request_timeout_seconds,
                user_agent=config.settings.user_agent,
            )
        )
    if normalized == "discord":
        webhook = _normalize_url(settings.get("webhook_url"))
        if not webhook:
            return None
        return DiscordNotifier(
            DiscordSettings(
                webhook_url=webhook,
                timeout_seconds=config.settings.request_timeout_seconds,
                user_agent=config.settings.user_agent,
            )
        )
    if normalized == "webhook":
        url = _normalize_url(settings.get("url"))
        if not url:
            return None
        headers = settings.get("headers")
        if headers is None:
            headers = {}
        return WebhookNotifier(
            WebhookSettings(
                url=url,
                headers={str(k): str(v) for k, v in headers.items()},
                timeout_seconds=config.settings.request_timeout_seconds,
                user_agent=config.settings.user_agent,
            )
        )
    return None


def _normalize_url(value: Any) -> str | None:
    if not value or not isinstance(value, str):
        return None
    if "${" in value:
        return None
    if not (value.startswith("http://") or value.startswith("https://")):
        return None
    return value


def build_notification_message(
    item: FeedItem,
    reasons: list[str],
    match: MatchResult | None,
    score: AlertScore | None,
) -> tuple[NotificationMessage, NotificationMetadata]:
    summary = item.description or item.title
    affected = {
        "packages": item.affected_packages,
        "services": item.affected_services,
        "cloud": item.affected_cloud,
    }
    message = NotificationMessage(
        title=item.title,
        summary=summary,
        priority=score.priority if score else "P3",
        score=score.score if score else 0,
        url=item.url,
        source=item.source,
        published=item.published,
        affected={key: [value for value in values if value] for key, values in affected.items()},
        tags=item.tags,
    )
    metadata = NotificationMetadata(
        reasons=reasons or [],
        rationale=score.rationale if score else [],
    )
    return message, metadata
