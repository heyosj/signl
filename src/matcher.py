from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import Iterable

from .config import StackConfig
from .dependencies.normalize import normalize_package_name
from .dependencies.types import DependencyGraph
from .feeds.base import FeedItem


_SHORT_TOKEN = re.compile(r"\b{}\b")

DEFAULT_SYNONYMS = {
    "kubernetes": ["k8s", "aks", "eks", "gke"],
    "entra-id": ["azure ad", "azure-ad", "entra"],
    "aws": ["amazon web services", "amazon aws"],
}


@dataclass
class MatchDetails:
    direct_package_hits: set[str] = field(default_factory=set)
    transitive_package_hits: set[str] = field(default_factory=set)
    service_hits: set[str] = field(default_factory=set)
    cloud_hits: set[str] = field(default_factory=set)
    keyword_hits: set[str] = field(default_factory=set)
    language_hits: set[str] = field(default_factory=set)
    alias_hits: set[str] = field(default_factory=set)


@dataclass
class MatchResult:
    is_relevant: bool
    reasons: list[str]
    details: MatchDetails


def calculate_relevance(
    item: FeedItem,
    config: StackConfig,
    dependencies: DependencyGraph,
) -> MatchResult:
    """
    Returns MatchResult with reasons and detailed match signals.
    """
    reasons: list[str] = []
    details = MatchDetails()
    text = f"{item.title} {item.description}".lower()
    match_config = config.match

    synonym_index, synonyms_by_canonical = _build_synonym_maps(config.synonyms, match_config.synonyms)

    direct_packages, transitive_packages = _build_package_sets(config, dependencies, match_config.normalize_names)

    _match_packages(
        item,
        text,
        match_config,
        synonym_index,
        synonyms_by_canonical,
        direct_packages,
        transitive_packages,
        details,
        reasons,
    )
    _match_services(
        text,
        item.affected_services,
        config.services,
        synonyms_by_canonical,
        match_config,
        details,
        reasons,
    )
    _match_cloud(
        text,
        item.affected_cloud,
        config.cloud,
        synonyms_by_canonical,
        match_config,
        details,
        reasons,
    )
    _match_keywords(text, config.keywords, details, reasons)
    _match_languages(text, config.languages, details, reasons)

    reasons = sorted(set(reasons))
    return MatchResult(is_relevant=bool(reasons), reasons=reasons, details=details)


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


def _build_synonym_maps(
    custom: dict[str, list[str]],
    enabled: bool,
) -> tuple[dict[str, str], dict[str, set[str]]]:
    if not enabled:
        return {}, {}
    alias_to_canonical: dict[str, str] = {}
    canonical_to_aliases: dict[str, set[str]] = {}
    for canonical, aliases in DEFAULT_SYNONYMS.items():
        _register_aliases(alias_to_canonical, canonical_to_aliases, canonical, aliases)
    for canonical, aliases in custom.items():
        _register_aliases(alias_to_canonical, canonical_to_aliases, canonical, aliases)
    return alias_to_canonical, canonical_to_aliases


def _register_aliases(
    alias_to_canonical: dict[str, str],
    canonical_to_aliases: dict[str, set[str]],
    canonical: str,
    aliases: Iterable[str],
) -> None:
    canonical_norm = canonical.strip().lower()
    if not canonical_norm:
        return
    for alias in aliases:
        alias_norm = alias.strip().lower()
        if alias_norm:
            alias_to_canonical[alias_norm] = canonical_norm
            canonical_to_aliases.setdefault(canonical_norm, set()).add(alias_norm)


def _build_package_sets(
    config: StackConfig,
    dependencies: DependencyGraph,
    normalize_names: bool,
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    direct: dict[str, set[str]] = {}
    transitive: dict[str, set[str]] = {}

    for ecosystem, packages in config.packages.items():
        eco = ecosystem.lower()
        direct.setdefault(eco, set()).update(
            normalize_package_name(pkg, eco, normalize_names) for pkg in packages
        )

    for ecosystem, packages in dependencies.direct.items():
        eco = ecosystem.lower()
        direct.setdefault(eco, set()).update(
            normalize_package_name(pkg, eco, normalize_names) for pkg in packages
        )

    for ecosystem, packages in dependencies.transitive.items():
        eco = ecosystem.lower()
        transitive.setdefault(eco, set()).update(
            normalize_package_name(pkg, eco, normalize_names) for pkg in packages
        )

    return direct, transitive


def _match_packages(
    item: FeedItem,
    text: str,
    match_config,
    synonym_index: dict[str, str],
    synonyms_by_canonical: dict[str, set[str]],
    direct_packages: dict[str, set[str]],
    transitive_packages: dict[str, set[str]],
    details: MatchDetails,
    reasons: list[str],
) -> None:
    if not item.affected_packages:
        _match_package_mentions(
            text,
            match_config,
            synonym_index,
            synonyms_by_canonical,
            direct_packages,
            reasons,
            details,
        )
        return

    item_ecosystems = _lower_set(item.ecosystems)
    ecosystems = item_ecosystems if item_ecosystems else set(direct_packages.keys()) | set(
        transitive_packages.keys()
    )

    for ecosystem in ecosystems:
        if not ecosystem:
            continue
        for pkg in item.affected_packages:
            normalized = normalize_package_name(pkg, ecosystem, match_config.normalize_names)
            if normalized in direct_packages.get(ecosystem, set()):
                details.direct_package_hits.add(normalized)
                reasons.append(f"Direct package match: {pkg}")
                continue
            if match_config.mode == "loose":
                alias = synonym_index.get(normalized)
                if alias and alias in direct_packages.get(ecosystem, set()):
                    details.alias_hits.add(normalized)
                    reasons.append(f"Package alias match: {pkg} -> {alias}")
                    continue
            if normalized in transitive_packages.get(ecosystem, set()):
                details.transitive_package_hits.add(normalized)
                reasons.append(f"Transitive package match: {pkg}")
                continue
            if match_config.mode == "loose":
                alias = synonym_index.get(normalized)
                if alias and alias in transitive_packages.get(ecosystem, set()):
                    details.alias_hits.add(normalized)
                    reasons.append(f"Transitive alias match: {pkg} -> {alias}")


def _match_package_mentions(
    text: str,
    match_config,
    synonym_index: dict[str, str],
    synonyms_by_canonical: dict[str, set[str]],
    direct_packages: dict[str, set[str]],
    reasons: list[str],
    details: MatchDetails,
) -> None:
    for ecosystem, packages in direct_packages.items():
        for pkg in packages:
            token = pkg.lower()
            if _contains_token(text, token):
                details.direct_package_hits.add(token)
                reasons.append(f"Package mentioned: {pkg}")
                continue
            if match_config.mode == "loose":
                aliases = synonyms_by_canonical.get(token, set())
                for alias in aliases:
                    if _contains_token(text, alias):
                        details.alias_hits.add(token)
                        reasons.append(f"Package alias mention: {alias} -> {token}")
                        break


def _match_services(
    text: str,
    affected: Iterable[str],
    services: list[str],
    synonyms_by_canonical: dict[str, set[str]],
    match_config,
    details: MatchDetails,
    reasons: list[str],
) -> None:
    affected_set = _lower_set(affected)
    for service in services:
        token = service.lower()
        if token in affected_set or _contains_token(text, token):
            details.service_hits.add(token)
            reasons.append(f"Service match: {service}")
            continue
        if match_config.mode == "loose":
            aliases = synonyms_by_canonical.get(token, set())
            for alias in aliases:
                if alias in affected_set or _contains_token(text, alias):
                    details.service_hits.add(token)
                    reasons.append(f"Service alias match: {alias} -> {service}")
                    break


def _match_cloud(
    text: str,
    affected: Iterable[str],
    clouds: list[str],
    synonyms_by_canonical: dict[str, set[str]],
    match_config,
    details: MatchDetails,
    reasons: list[str],
) -> None:
    affected_set = _lower_set(affected)
    for provider in clouds:
        token = provider.lower()
        if token in affected_set or _contains_token(text, token):
            details.cloud_hits.add(token)
            reasons.append(f"Cloud match: {provider}")
            continue
        if match_config.mode == "loose":
            aliases = synonyms_by_canonical.get(token, set())
            for alias in aliases:
                if alias in affected_set or _contains_token(text, alias):
                    details.cloud_hits.add(token)
                    reasons.append(f"Cloud alias match: {alias} -> {provider}")
                    break


def _match_keywords(
    text: str,
    keywords: list[str],
    details: MatchDetails,
    reasons: list[str],
) -> None:
    for keyword in keywords:
        token = keyword.lower()
        if _contains_token(text, token):
            details.keyword_hits.add(token)
            reasons.append(f"Keyword match: {keyword}")


def _match_languages(
    text: str,
    languages: list[str],
    details: MatchDetails,
    reasons: list[str],
) -> None:
    for language in languages:
        token = language.lower()
        if _contains_token(text, token):
            details.language_hits.add(token)
            reasons.append(f"Language match: {language}")
