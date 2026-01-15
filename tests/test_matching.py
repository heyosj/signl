from __future__ import annotations

import unittest

from src.config import StackConfig, StackDepsConfig, StackMatchConfig, AssetCriticalityConfig
from src.dependencies.types import DependencyGraph
from src.feeds.base import FeedItem
from src.matcher import calculate_relevance
from datetime import datetime, timezone


class MatchingTests(unittest.TestCase):
    def _stack(self, mode: str) -> StackConfig:
        return StackConfig(
            cloud=["azure"],
            languages=["python"],
            packages={"npm": ["lodash"]},
            services=["kubernetes"],
            keywords=[],
            deps=StackDepsConfig(enabled=False, sources=[], include_transitive=False, ecosystems=[]),
            match=StackMatchConfig(mode=mode, synonyms=True, normalize_names=True),
            synonyms={},
            asset_criticality=AssetCriticalityConfig(services={}, packages={}),
        )

    def test_synonym_matching_loose(self) -> None:
        item = FeedItem(
            id="test",
            source="rss",
            title="K8s CVE",
            description="Issue in k8s clusters.",
            url="https://example.com",
            published=datetime.now(timezone.utc),
            severity=None,
            cvss_score=None,
            affected_packages=[],
            raw_data={},
        )
        match = calculate_relevance(item, self._stack("loose"), DependencyGraph())
        self.assertTrue(match.is_relevant)
        self.assertTrue(any("Service" in reason for reason in match.reasons))

    def test_synonym_strict_mode(self) -> None:
        item = FeedItem(
            id="test",
            source="rss",
            title="K8s advisory",
            description="k8s issue",
            url="https://example.com",
            published=datetime.now(timezone.utc),
            severity=None,
            cvss_score=None,
            affected_packages=[],
            raw_data={},
        )
        match = calculate_relevance(item, self._stack("strict"), DependencyGraph())
        self.assertFalse(match.is_relevant)
