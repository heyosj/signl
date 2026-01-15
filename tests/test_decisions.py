import unittest
from datetime import datetime, timezone

from src.decisions import classify_alert
from src.feeds.base import FeedItem
from src.matcher import MatchDetails, MatchResult
from src.scoring import AlertScore


def _make_item(
    title: str = "Test alert",
    description: str = "Test description",
    source: str = "nvd",
    tags: list[str] | None = None,
    affected_packages: list[str] | None = None,
) -> FeedItem:
    return FeedItem(
        id="test",
        source=source,
        title=title,
        description=description,
        url="https://example.com",
        published=datetime.now(timezone.utc),
        severity=None,
        cvss_score=None,
        affected_packages=affected_packages or [],
        raw_data={},
        tags=tags or [],
    )


def _make_match(details: MatchDetails | None = None) -> MatchResult:
    return MatchResult(
        is_relevant=True,
        reasons=["Direct package match: lodash"],
        details=details or MatchDetails(direct_package_hits={"lodash"}),
    )


class DecisionTests(unittest.TestCase):
    def test_quiet_suppresses_non_exploited_high_severity(self) -> None:
        item = _make_item()
        match = _make_match()
        score = AlertScore(score=90, priority="P0", rationale=[])
        decision = classify_alert(item, match, score, "quiet", [], True)
        self.assertFalse(decision.immediate)

    def test_quiet_allows_kev(self) -> None:
        item = _make_item(source="cisa", tags=["kev"])
        match = _make_match()
        score = AlertScore(score=10, priority="P3", rationale=[])
        decision = classify_alert(item, match, score, "quiet", [], True)
        self.assertTrue(decision.immediate)

    def test_always_page_bypasses_quiet(self) -> None:
        item = _make_item(title="TruffleHog detected")
        match = _make_match()
        score = AlertScore(score=10, priority="P3", rationale=[])
        decision = classify_alert(item, match, score, "quiet", ["trufflehog"], True)
        self.assertTrue(decision.immediate)
        self.assertTrue(decision.matched_always_page)

    def test_loud_pages_on_any_relevant_alert(self) -> None:
        item = _make_item()
        details = MatchDetails(keyword_hits={"kubernetes"})
        match = _make_match(details)
        score = AlertScore(score=5, priority="P3", rationale=[])
        decision = classify_alert(item, match, score, "loud", [], True)
        self.assertTrue(decision.immediate)

    def test_default_behavior_when_mode_absent(self) -> None:
        item = _make_item()
        details = MatchDetails(keyword_hits={"kubernetes"})
        match = _make_match(details)
        score = AlertScore(score=5, priority="P3", rationale=[])
        decision = classify_alert(item, match, score, "normal", [], False)
        self.assertTrue(decision.immediate)
