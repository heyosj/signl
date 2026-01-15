from __future__ import annotations

from dataclasses import dataclass

from .feeds.base import FeedItem
from .matcher import MatchResult
from .scoring import AlertScore


TRUSTED_SOURCES = {"cisa", "msrc", "osv", "github"}
EXPLOIT_PHRASES = (
    "exploited in the wild",
    "actively exploited",
    "active exploitation",
    "in the wild",
)
CAMPAIGN_PHRASES = (
    "threat actor",
    "active campaign",
    "campaign",
    "apt",
    "ransomware",
)


@dataclass
class AlertDecision:
    immediate: bool
    reason: str
    mode: str
    matched_always_page: bool


def classify_alert(
    item: FeedItem,
    match: MatchResult,
    score: AlertScore,
    mode: str,
    always_page: list[str],
    mode_explicit: bool,
) -> AlertDecision:
    matched_keyword = _match_always_page(item, match, always_page)
    if matched_keyword:
        return AlertDecision(
            immediate=True,
            reason=f'matched always_page keyword "{matched_keyword}"',
            mode=mode,
            matched_always_page=True,
        )

    if not mode_explicit:
        return AlertDecision(
            immediate=True,
            reason="relevant to stack (legacy default)",
            mode=mode,
            matched_always_page=False,
        )

    confidence, confidence_reason = _confidence_signal(item)
    relevance_level = _relevance_level(match)
    high_severity = score.priority in {"P0", "P1"}

    if mode == "quiet":
        if confidence:
            return AlertDecision(
                immediate=True,
                reason=f"relevant + {confidence_reason}",
                mode=mode,
                matched_always_page=False,
            )
        return AlertDecision(
            immediate=False,
            reason="quiet mode: relevant but no high-confidence signal",
            mode=mode,
            matched_always_page=False,
        )

    if mode == "loud":
        return AlertDecision(
            immediate=True,
            reason="relevant to stack (loud mode)",
            mode=mode,
            matched_always_page=False,
        )

    if relevance_level in {"medium", "low"}:
        return AlertDecision(
            immediate=False,
            reason="normal mode: lower relevance routed to digest",
            mode=mode,
            matched_always_page=False,
        )

    if high_severity or confidence:
        reason_bits = []
        if high_severity:
            reason_bits.append("high severity")
        if confidence:
            reason_bits.append(confidence_reason)
        reason = "relevant + " + " + ".join(reason_bits)
        return AlertDecision(
            immediate=True,
            reason=reason,
            mode=mode,
            matched_always_page=False,
        )

    return AlertDecision(
        immediate=False,
        reason="normal mode: relevant but not severe/high-confidence",
        mode=mode,
        matched_always_page=False,
    )


def _match_always_page(item: FeedItem, match: MatchResult, always_page: list[str]) -> str | None:
    if not match.is_relevant or not always_page:
        return None
    text_bits = [
        item.title,
        item.description,
        " ".join(item.affected_packages),
        " ".join(item.affected_services),
    ]
    haystack = " ".join(bit for bit in text_bits if bit).lower()
    for keyword in always_page:
        needle = keyword.strip().lower()
        if needle and needle in haystack:
            return keyword
    return None


def _confidence_signal(item: FeedItem) -> tuple[bool, str]:
    if item.source.lower() == "cisa" or "kev" in [tag.lower() for tag in item.tags]:
        return True, "CISA KEV"

    text = f"{item.title} {item.description}".lower()
    for phrase in EXPLOIT_PHRASES:
        if phrase in text:
            return True, "exploited in the wild"
    for phrase in CAMPAIGN_PHRASES:
        if phrase in text:
            return True, "active campaign or threat actor mention"
    if item.source.lower() in TRUSTED_SOURCES:
        return True, f"trusted source ({item.source.upper()})"
    return False, "no high-confidence signal"


def _relevance_level(match: MatchResult) -> str:
    details = match.details
    if details.direct_package_hits or details.service_hits or details.cloud_hits:
        return "high"
    if details.transitive_package_hits or details.alias_hits:
        return "medium"
    if details.keyword_hits or details.language_hits:
        return "low"
    return "low"
