from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math

from .config import ScoringConfig, StackConfig
from .feeds.base import FeedItem
from .matcher import MatchResult


@dataclass
class AlertScore:
    score: int
    priority: str
    rationale: list[str]


SEVERITY_MAP = {
    "critical": 90,
    "high": 75,
    "medium": 55,
    "low": 30,
}


def score_alert(
    item: FeedItem,
    match: MatchResult,
    scoring: ScoringConfig,
    stack: StackConfig,
) -> AlertScore:
    if not scoring.enabled:
        return AlertScore(score=0, priority="P3", rationale=["Scoring disabled"])

    severity_score, severity_reason = _score_severity(item)
    exploitability_score, exploitability_reasons = _score_exploitability(item, scoring)
    relevance_score, relevance_reasons = _score_relevance(match, stack)
    recency_score, recency_reason = _score_recency(item)

    weights = scoring.weights
    weighted = (
        severity_score * weights.get("severity", 0.45)
        + exploitability_score * weights.get("exploitability", 0.25)
        + relevance_score * weights.get("relevance", 0.2)
        + recency_score * weights.get("recency", 0.1)
    )
    boost = _source_boost(item, scoring)
    total = min(100, int(round(weighted + boost)))

    rationale: list[str] = []
    if severity_reason:
        rationale.append(severity_reason)
    rationale.extend(exploitability_reasons)
    rationale.extend(relevance_reasons)
    if recency_reason:
        rationale.append(recency_reason)
    if boost:
        rationale.append(f"Preferred source boost (+{boost})")

    priority = _priority_for_score(total, scoring)
    return AlertScore(score=total, priority=priority, rationale=rationale)


def _score_severity(item: FeedItem) -> tuple[int, str | None]:
    if item.cvss_score is not None:
        score = int(round(min(max(item.cvss_score, 0.0), 10.0) * 10))
        return score, f"CVSS {item.cvss_score:.1f}"
    if item.severity:
        mapped = SEVERITY_MAP.get(item.severity.lower())
        if mapped is not None:
            return mapped, f"Vendor severity {item.severity.lower()}"
    return 0, None


def _score_exploitability(item: FeedItem, scoring: ScoringConfig) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    text = f"{item.title} {item.description}".lower()
    if item.source.lower() == "cisa" or "kev" in [tag.lower() for tag in item.tags]:
        score += 60
        reasons.append("CISA KEV listed")
    for keyword in scoring.keywords.get("exploited_in_wild", []):
        if keyword.lower() in text:
            score += 20
            reasons.append("Exploited in the wild keyword")
            break
    for keyword in scoring.keywords.get("poc", []):
        if keyword.lower() in text:
            score += 10
            reasons.append("PoC keyword")
            break
    epss = _extract_epss(item.raw_data)
    if epss is not None and epss >= 0.5:
        score += 10
        reasons.append(f"EPSS {epss:.2f}")
    return min(score, 100), reasons


def _extract_epss(raw: dict) -> float | None:
    for key in ("epss", "epssScore", "epss_score"):
        value = raw.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _score_relevance(match: MatchResult, stack: StackConfig) -> tuple[int, list[str]]:
    reasons: list[str] = []
    details = match.details
    score = 0
    if details.direct_package_hits:
        score = 100
        reasons.append("Direct dependency match")
    elif details.transitive_package_hits:
        score = 70
        reasons.append("Transitive dependency match")
    elif details.service_hits:
        score = 60
        reasons.append("Service match")
    elif details.cloud_hits:
        score = 50
        reasons.append("Cloud match")
    elif details.keyword_hits:
        score = 35
        reasons.append("Keyword match")
    elif details.language_hits:
        score = 25
        reasons.append("Language match")

    criticality_boost = _criticality_boost(details, stack)
    if criticality_boost:
        score = min(100, int(round(score + criticality_boost)))
        reasons.append("Critical asset boost")
    return score, reasons


def _criticality_boost(details, stack: StackConfig) -> float:
    boost = 0.0
    for service in details.service_hits:
        weight = stack.asset_criticality.services.get(service)
        if weight:
            boost = max(boost, 10.0 * weight)
    for package in details.direct_package_hits | details.transitive_package_hits:
        weight = stack.asset_criticality.packages.get(package)
        if weight:
            boost = max(boost, 10.0 * weight)
    return boost


def _score_recency(item: FeedItem) -> tuple[int, str | None]:
    now = datetime.now(timezone.utc)
    published = item.published
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (now - published).total_seconds() / 86400)
    score = max(0, int(round(100 - age_days * 3)))
    if score <= 0:
        return 0, None
    return score, f"Recency {math.ceil(age_days)}d old"


def _source_boost(item: FeedItem, scoring: ScoringConfig) -> int:
    preferred = {source.lower() for source in scoring.prefer_sources}
    if item.source.lower() in preferred:
        return 3
    return 0


def _priority_for_score(score: int, scoring: ScoringConfig) -> str:
    thresholds = scoring.thresholds
    if score >= thresholds.get("P0", 85):
        return "P0"
    if score >= thresholds.get("P1", 70):
        return "P1"
    if score >= thresholds.get("P2", 50):
        return "P2"
    return "P3"
