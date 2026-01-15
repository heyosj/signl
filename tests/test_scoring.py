from __future__ import annotations

import unittest
from datetime import datetime, timezone

from src.config import AssetCriticalityConfig, ScoringConfig, StackConfig, StackDepsConfig, StackMatchConfig
from src.feeds.base import FeedItem
from src.matcher import MatchDetails, MatchResult
from src.scoring import score_alert


def _stack() -> StackConfig:
    return StackConfig(
        cloud=[],
        languages=[],
        packages={},
        services=[],
        keywords=[],
        deps=StackDepsConfig(enabled=False, sources=[], include_transitive=False, ecosystems=[]),
        match=StackMatchConfig(mode="loose", synonyms=True, normalize_names=True),
        synonyms={},
        asset_criticality=AssetCriticalityConfig(services={}, packages={}),
    )


def _scoring() -> ScoringConfig:
    return ScoringConfig(
        enabled=True,
        weights={"severity": 0.45, "exploitability": 0.25, "relevance": 0.2, "recency": 0.1},
        thresholds={"P0": 85, "P1": 70, "P2": 50, "P3": 0},
        prefer_sources=["cisa"],
        keywords={
            "exploited_in_wild": ["exploited in the wild"],
            "poc": ["proof of concept"],
        },
    )


class ScoringTests(unittest.TestCase):
    def test_cvss_and_kev_hits_p0(self) -> None:
        item = FeedItem(
            id="cve",
            source="nvd",
            title="CVE-0000-0000",
            description="Test",
            url="https://example.com",
            published=datetime.now(timezone.utc),
            severity="critical",
            cvss_score=9.8,
            affected_packages=[],
            raw_data={},
            tags=["kev"],
        )
        details = MatchDetails(direct_package_hits={"lodash"})
        match = MatchResult(is_relevant=True, reasons=["Direct package match"], details=details)
        score = score_alert(item, match, _scoring(), _stack())
        self.assertEqual(score.priority, "P0")

    def test_transitive_medium_scores_lower(self) -> None:
        item = FeedItem(
            id="medium",
            source="github",
            title="GHSA-1",
            description="Test",
            url="https://example.com",
            published=datetime.now(timezone.utc),
            severity="medium",
            cvss_score=None,
            affected_packages=[],
            raw_data={},
        )
        details = MatchDetails(transitive_package_hits={"requests"})
        match = MatchResult(is_relevant=True, reasons=["Transitive match"], details=details)
        score = score_alert(item, match, _scoring(), _stack())
        self.assertLess(score.score, 50)
        self.assertEqual(score.priority, "P3")

    def test_vendor_severity_mapping(self) -> None:
        item = FeedItem(
            id="vendor",
            source="rss",
            title="Vendor alert",
            description="Test",
            url="https://example.com",
            published=datetime.now(timezone.utc),
            severity="critical",
            cvss_score=None,
            affected_packages=[],
            raw_data={},
        )
        details = MatchDetails(service_hits={"kubernetes"})
        match = MatchResult(is_relevant=True, reasons=["Service match"], details=details)
        score = score_alert(item, match, _scoring(), _stack())
        self.assertGreater(score.score, 0)
        self.assertTrue(any("Vendor severity" in reason for reason in score.rationale))
