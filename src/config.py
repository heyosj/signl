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
    deps: StackDepsConfig
    match: StackMatchConfig
    synonyms: dict[str, list[str]]
    asset_criticality: AssetCriticalityConfig


@dataclass
class NotifierTarget:
    type: str
    settings: dict[str, Any]


@dataclass
class NotificationConfig:
    targets: list[NotifierTarget]
    used_legacy: bool


@dataclass
class Settings:
    poll_interval_minutes: int
    state_file: str
    include_low_severity: bool
    max_results_per_feed: int
    request_timeout_seconds: int
    user_agent: str
    max_notifications_per_run: int
    min_cvss_score: float | None


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
    scoring: ScoringConfig


@dataclass
class StackDepsSource:
    type: str
    path: str


@dataclass
class StackDepsConfig:
    enabled: bool
    sources: list[StackDepsSource]
    include_transitive: bool
    ecosystems: list[str]


@dataclass
class StackMatchConfig:
    mode: str
    synonyms: bool
    normalize_names: bool


@dataclass
class AssetCriticalityConfig:
    services: dict[str, float]
    packages: dict[str, float]


@dataclass
class ScoringConfig:
    enabled: bool
    weights: dict[str, float]
    thresholds: dict[str, int]
    prefer_sources: list[str]
    keywords: dict[str, list[str]]


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

    stack = _load_stack(_require_dict(data.get("stack"), "stack"))

    notifications = _load_notifications(data)

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
        max_notifications_per_run=int(settings_raw.get("max_notifications_per_run", 25)),
        min_cvss_score=_parse_min_cvss(settings_raw.get("min_cvss_score")),
    )

    feeds = _load_feeds(_require_dict(data.get("feeds"), "feeds"))
    scoring = _load_scoring(_require_dict(data.get("scoring"), "scoring"))

    return Config(
        stack=stack,
        notifications=notifications,
        settings=settings,
        feeds=feeds,
        scoring=scoring,
    )


def _load_stack(raw: dict[str, Any]) -> StackConfig:
    deps = _load_deps(_require_dict(raw.get("deps"), "stack.deps"))
    match = _load_match(_require_dict(raw.get("match"), "stack.match"))
    synonyms = _normalize_synonyms(raw.get("synonyms"))
    asset_criticality = _load_asset_criticality(
        _require_dict(raw.get("asset_criticality"), "stack.asset_criticality")
    )
    return StackConfig(
        cloud=_require_list(raw.get("cloud"), "stack.cloud"),
        languages=_require_list(raw.get("languages"), "stack.languages"),
        packages=_normalize_packages(raw.get("packages")),
        services=_require_list(raw.get("services"), "stack.services"),
        keywords=_require_list(raw.get("keywords"), "stack.keywords"),
        deps=deps,
        match=match,
        synonyms=synonyms,
        asset_criticality=asset_criticality,
    )


def _load_deps(raw: dict[str, Any]) -> StackDepsConfig:
    sources_raw = raw.get("sources", [])
    sources: list[StackDepsSource] = []
    if sources_raw:
        if not isinstance(sources_raw, list):
            raise ValueError("stack.deps.sources must be a list")
        for entry in sources_raw:
            if not isinstance(entry, dict):
                raise ValueError("stack.deps.sources entries must be mappings")
            source_type = entry.get("type")
            path = entry.get("path")
            if not source_type or not path:
                raise ValueError("stack.deps.sources entries must include type and path")
            sources.append(StackDepsSource(type=str(source_type), path=str(path)))

    return StackDepsConfig(
        enabled=bool(raw.get("enabled", False)),
        sources=sources,
        include_transitive=bool(raw.get("include_transitive", True)),
        ecosystems=_require_list(raw.get("ecosystems"), "stack.deps.ecosystems"),
    )


def _load_match(raw: dict[str, Any]) -> StackMatchConfig:
    mode = str(raw.get("mode", "loose")).lower()
    if mode not in {"strict", "loose"}:
        raise ValueError("stack.match.mode must be 'strict' or 'loose'")
    return StackMatchConfig(
        mode=mode,
        synonyms=bool(raw.get("synonyms", True)),
        normalize_names=bool(raw.get("normalize_names", True)),
    )


def _normalize_synonyms(value: Any) -> dict[str, list[str]]:
    raw = _require_dict(value, "stack.synonyms")
    normalized: dict[str, list[str]] = {}
    for canonical, aliases in raw.items():
        if aliases is None:
            normalized[str(canonical)] = []
            continue
        if not isinstance(aliases, list):
            raise ValueError("stack.synonyms values must be lists")
        normalized[str(canonical)] = [str(item) for item in aliases]
    return normalized


def _load_asset_criticality(raw: dict[str, Any]) -> AssetCriticalityConfig:
    return AssetCriticalityConfig(
        services=_normalize_weight_map(raw.get("services"), "stack.asset_criticality.services"),
        packages=_normalize_weight_map(raw.get("packages"), "stack.asset_criticality.packages"),
    )


def _normalize_weight_map(value: Any, name: str) -> dict[str, float]:
    if value is None:
        return {}
    if isinstance(value, list):
        return {str(item).lower(): 1.0 for item in value}
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a list or mapping")
    normalized: dict[str, float] = {}
    for key, weight in value.items():
        try:
            normalized[str(key).lower()] = float(weight)
        except (TypeError, ValueError):
            raise ValueError(f"{name} values must be numbers")
    return normalized


def _load_notifications(data: dict[str, Any]) -> NotificationConfig:
    targets: list[NotifierTarget] = []
    used_legacy = False

    notify_raw = data.get("notify", [])
    if notify_raw:
        if not isinstance(notify_raw, list):
            raise ValueError("notify must be a list")
        for entry in notify_raw:
            if not isinstance(entry, dict):
                raise ValueError("notify entries must be mappings")
            target_type = entry.get("type")
            if not target_type:
                raise ValueError("notify entries must include type")
            settings = {k: v for k, v in entry.items() if k != "type"}
            targets.append(NotifierTarget(type=str(target_type), settings=settings))

    notifications_raw = _require_dict(data.get("notifications"), "notifications")
    discord_raw = _require_dict(notifications_raw.get("discord"), "notifications.discord")
    slack_raw = _require_dict(notifications_raw.get("slack"), "notifications.slack")
    discord_url = _normalize_webhook(discord_raw.get("webhook_url"))
    slack_url = _normalize_webhook(slack_raw.get("webhook_url"))
    if discord_url:
        used_legacy = True
        targets.append(NotifierTarget(type="discord", settings={"webhook_url": discord_url}))
    if slack_url:
        used_legacy = True
        targets.append(NotifierTarget(type="slack", settings={"webhook_url": slack_url}))

    return NotificationConfig(targets=targets, used_legacy=used_legacy)


def _load_scoring(raw: dict[str, Any]) -> ScoringConfig:
    weights_raw = _require_dict(raw.get("weights"), "scoring.weights")
    thresholds_raw = _require_dict(raw.get("thresholds"), "scoring.thresholds")
    keywords_raw = _require_dict(raw.get("keywords"), "scoring.keywords")
    weights = {
        "severity": float(weights_raw.get("severity", 0.45)),
        "exploitability": float(weights_raw.get("exploitability", 0.25)),
        "relevance": float(weights_raw.get("relevance", 0.2)),
        "recency": float(weights_raw.get("recency", 0.1)),
    }
    thresholds = {
        "P0": int(thresholds_raw.get("P0", 85)),
        "P1": int(thresholds_raw.get("P1", 70)),
        "P2": int(thresholds_raw.get("P2", 50)),
        "P3": int(thresholds_raw.get("P3", 0)),
    }
    keywords = {
        "exploited_in_wild": _require_list(
            keywords_raw.get("exploited_in_wild"), "scoring.keywords.exploited_in_wild"
        ),
        "poc": _require_list(keywords_raw.get("poc"), "scoring.keywords.poc"),
    }
    return ScoringConfig(
        enabled=bool(raw.get("enabled", True)),
        weights=weights,
        thresholds=thresholds,
        prefer_sources=_require_list(raw.get("prefer_sources"), "scoring.prefer_sources"),
        keywords=keywords,
    )


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


def _normalize_webhook(value: Any) -> str | None:
    if not value or not isinstance(value, str):
        return None
    if "${" in value:
        return None
    if not (value.startswith("http://") or value.startswith("https://")):
        return None
    return value


def _parse_min_cvss(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError("settings.min_cvss_score must be a number or null")
