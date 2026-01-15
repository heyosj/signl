from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

import yaml


@dataclass
class StackConfig:
    cloud: list[str]
    languages: list[str]
    packages: dict[str, list[str]]
    services: list[str]
    keywords: list[str]


@dataclass
class NotificationConfig:
    discord_webhook_url: str | None
    slack_webhook_url: str | None


@dataclass
class Settings:
    poll_interval_minutes: int
    state_file: str
    include_low_severity: bool
    max_results_per_feed: int
    request_timeout_seconds: int
    user_agent: str


@dataclass
class RSSFeedConfig:
    name: str
    url: str


@dataclass
class HackerNewsConfig:
    enabled: bool
    max_terms: int


@dataclass
class OSVConfig:
    enabled: bool


@dataclass
class CISAConfig:
    enabled: bool


@dataclass
class FeedsConfig:
    nvd: bool
    github: bool
    msrc: bool
    rss: list[RSSFeedConfig]
    hackernews: HackerNewsConfig
    osv: OSVConfig
    cisa: CISAConfig


@dataclass
class Config:
    stack: StackConfig
    notifications: NotificationConfig
    settings: Settings
    feeds: FeedsConfig


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand_env(val) for key, val in value.items()}
    return value


def _require_dict(value: Any, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a mapping")
    return value


def _require_list(value: Any, name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a list")
    return [str(item) for item in value]


def load_config(path: str) -> Config:
    with open(path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    data = _expand_env(raw)
    if not isinstance(data, dict):
        raise ValueError("Config root must be a mapping")

    stack_raw = _require_dict(data.get("stack"), "stack")
    stack = StackConfig(
        cloud=_require_list(stack_raw.get("cloud"), "stack.cloud"),
        languages=_require_list(stack_raw.get("languages"), "stack.languages"),
        packages=_normalize_packages(stack_raw.get("packages")),
        services=_require_list(stack_raw.get("services"), "stack.services"),
        keywords=_require_list(stack_raw.get("keywords"), "stack.keywords"),
    )

    notifications_raw = _require_dict(data.get("notifications"), "notifications")
    discord_raw = _require_dict(notifications_raw.get("discord"), "notifications.discord")
    slack_raw = _require_dict(notifications_raw.get("slack"), "notifications.slack")
    notifications = NotificationConfig(
        discord_webhook_url=discord_raw.get("webhook_url"),
        slack_webhook_url=slack_raw.get("webhook_url"),
    )

    settings_raw = _require_dict(data.get("settings"), "settings")
    poll_interval = int(settings_raw.get("poll_interval_minutes", 15))
    if poll_interval < 5:
        raise ValueError("settings.poll_interval_minutes must be >= 5")

    settings = Settings(
        poll_interval_minutes=poll_interval,
        state_file=str(settings_raw.get("state_file", "./state.json")),
        include_low_severity=bool(settings_raw.get("include_low_severity", False)),
        max_results_per_feed=int(settings_raw.get("max_results_per_feed", 200)),
        request_timeout_seconds=int(settings_raw.get("request_timeout_seconds", 20)),
        user_agent=str(settings_raw.get("user_agent", "signl/0.1")),
    )

    feeds = _load_feeds(_require_dict(data.get("feeds"), "feeds"))

    return Config(stack=stack, notifications=notifications, settings=settings, feeds=feeds)


def _load_feeds(raw: dict[str, Any]) -> FeedsConfig:
    rss_raw = raw.get("rss", [])
    rss_list: list[RSSFeedConfig] = []
    if rss_raw:
        if not isinstance(rss_raw, list):
            raise ValueError("feeds.rss must be a list")
        for entry in rss_raw:
            if not isinstance(entry, dict):
                raise ValueError("feeds.rss entries must be mappings")
            name = entry.get("name")
            url = entry.get("url")
            if not name or not url:
                raise ValueError("feeds.rss entries must include name and url")
            rss_list.append(RSSFeedConfig(name=str(name), url=str(url)))

    hn_raw = _require_dict(raw.get("hackernews"), "feeds.hackernews")
    hn = HackerNewsConfig(
        enabled=bool(hn_raw.get("enabled", True)),
        max_terms=int(hn_raw.get("max_terms", 6)),
    )

    osv_raw = _require_dict(raw.get("osv"), "feeds.osv")
    osv = OSVConfig(enabled=bool(osv_raw.get("enabled", True)))

    cisa_raw = _require_dict(raw.get("cisa"), "feeds.cisa")
    cisa = CISAConfig(enabled=bool(cisa_raw.get("enabled", True)))

    return FeedsConfig(
        nvd=bool(raw.get("nvd", True)),
        github=bool(raw.get("github", True)),
        msrc=bool(raw.get("msrc", True)),
        rss=rss_list,
        hackernews=hn,
        osv=osv,
        cisa=cisa,
    )


def _normalize_packages(value: Any) -> dict[str, list[str]]:
    packages_raw = _require_dict(value, "stack.packages")
    normalized: dict[str, list[str]] = {}
    for ecosystem, names in packages_raw.items():
        if names is None:
            normalized[str(ecosystem)] = []
            continue
        if not isinstance(names, list):
            raise ValueError(f"stack.packages.{ecosystem} must be a list")
        normalized[str(ecosystem)] = [str(item) for item in names]
    return normalized
