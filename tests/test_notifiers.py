from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import httpx

from src.config import (
    AssetCriticalityConfig,
    Config,
    FeedsConfig,
    HackerNewsConfig,
    NotificationConfig,
    NotifierTarget,
    OSVConfig,
    CISAConfig,
    ScoringConfig,
    Settings,
    StackConfig,
    StackDepsConfig,
    StackMatchConfig,
)
from src.feeds.base import FeedItem
from src.matcher import MatchDetails, MatchResult
from src.notifiers.factory import build_notifiers, build_notification_message
from src.notifiers.webhook import WebhookNotifier
from src.scoring import AlertScore


class NotifierTests(unittest.IsolatedAsyncioTestCase):
    def _config(self) -> Config:
        return Config(
            stack=StackConfig(
                cloud=[],
                languages=[],
                packages={},
                services=[],
                keywords=[],
                deps=StackDepsConfig(enabled=False, sources=[], include_transitive=False, ecosystems=[]),
                match=StackMatchConfig(mode="loose", synonyms=True, normalize_names=True),
                synonyms={},
                asset_criticality=AssetCriticalityConfig(services={}, packages={}),
            ),
            notifications=NotificationConfig(
                targets=[
                    NotifierTarget(type="webhook", settings={"url": "https://example.com/hook"}),
                ],
                used_legacy=False,
            ),
            settings=Settings(
                poll_interval_minutes=15,
                state_file="./state.json",
                include_low_severity=False,
                max_results_per_feed=10,
                request_timeout_seconds=5,
                user_agent="signl/test",
                max_notifications_per_run=5,
                min_cvss_score=None,
            ),
            feeds=FeedsConfig(
                nvd=False,
                github=False,
                msrc=False,
                rss=[],
                hackernews=HackerNewsConfig(enabled=False, max_terms=1),
                osv=OSVConfig(enabled=False),
                cisa=CISAConfig(enabled=False),
            ),
            scoring=ScoringConfig(
                enabled=True,
                weights={"severity": 0.45, "exploitability": 0.25, "relevance": 0.2, "recency": 0.1},
                thresholds={"P0": 85, "P1": 70, "P2": 50, "P3": 0},
                prefer_sources=[],
                keywords={"exploited_in_wild": [], "poc": []},
            ),
        )

    async def test_webhook_payload_contains_priority(self) -> None:
        config = self._config()
        notifiers = build_notifiers(config)
        self.assertEqual(len(notifiers), 1)
        self.assertIsInstance(notifiers[0], WebhookNotifier)

        item = FeedItem(
            id="test",
            source="rss",
            title="Test alert",
            description="Summary",
            url="https://example.com",
            published=datetime.now(timezone.utc),
            severity=None,
            cvss_score=None,
            affected_packages=["requests"],
            raw_data={},
        )
        match = MatchResult(is_relevant=True, reasons=["Direct package match"], details=MatchDetails())
        score = AlertScore(score=88, priority="P0", rationale=["CVSS 9.8"])
        message, metadata = build_notification_message(item, match.reasons, match, score)

        with patch("httpx.AsyncClient") as mock_client:
            instance = mock_client.return_value.__aenter__.return_value
            instance.post = AsyncMock(return_value=httpx.Response(200))
            success = await notifiers[0].send(message, metadata)

        self.assertTrue(success)
        payload = instance.post.call_args.kwargs.get("json")
        self.assertEqual(payload["priority"], "P0")
        self.assertEqual(payload["score"], 88)
