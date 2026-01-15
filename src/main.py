from __future__ import annotations

# Plan:
# 1) Load config + dependency graph and normalize alerts with match/scoring.
# 2) Score matches, group by priority, and send via selected notifiers.
# 3) Preserve legacy config behavior with warnings and safe defaults.

import argparse
import asyncio
from datetime import datetime, timezone
import logging
from pathlib import Path

from .config import load_config
from .dependencies import DependenciesConfig, DependencySource, load_dependency_graph
from .feeds.cisa import CISAFeed, CISASettings
from .feeds.github import GitHubFeed, GitHubSettings
from .feeds.hackernews import HackerNewsFeed, HackerNewsSettings
from .feeds.msrc import MSRCFeed, MSRCSettings
from .feeds.nvd import NVDFeed, NVDSettings
from .feeds.osv import OSVFeed, OSVSettings
from .feeds.rss import RSSFeed, RSSSettings, RSSSource
from .matcher import calculate_relevance
from .notifiers.factory import build_notifiers, build_notification_message
from .state import load_state, mark_sent, prune_sent, save_state, was_sent
from .scoring import score_alert


async def main() -> None:
    args = _parse_args()
    if args.init_config:
        _init_config(Path(args.config))
        return
    config = load_config(args.config)
    _configure_logging(args.verbose)

    state = load_state(config.settings.state_file)

    feeds = _build_feeds(config)
    notifiers = build_notifiers(config)
    dependency_graph = _build_dependency_graph(config, Path(args.config))
    if not args.dry_run and not notifiers:
        raise SystemExit(
            "At least one notifier is required unless --dry-run is set. "
            "Set notify entries in config.yaml or configure notifications.slack/discord."
        )

    if args.test_notify:
        if not notifiers:
            raise SystemExit("At least one notifier is required for --test-notify")
        message, metadata = build_notification_message(
            _build_test_item(), ["Test notification"], None, None
        )
        for notifier in notifiers:
            await notifier.send(message, metadata)
        return

    while True:
        await _poll_once(
            feeds,
            notifiers,
            config,
            state,
            dependency_graph,
            dry_run=args.dry_run,
        )
        save_state(config.settings.state_file, state)
        if args.once:
            break
        await asyncio.sleep(config.settings.poll_interval_minutes * 60)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Security Stack News Notifier")
    parser.add_argument("--config", default="./config.yaml")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--init-config", action="store_true", help="Create a config.yaml template and exit")
    parser.add_argument("--test-notify", action="store_true", help="Send a test notification and exit")
    return parser.parse_args()


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def _build_feeds(config):
    settings = config.settings
    feeds = []

    if config.feeds.nvd:
        feeds.append(
            NVDFeed(
                NVDSettings(
                    max_results=settings.max_results_per_feed,
                    timeout_seconds=settings.request_timeout_seconds,
                    user_agent=settings.user_agent,
                )
            )
        )

    if config.feeds.github:
        feeds.append(
            GitHubFeed(
                GitHubSettings(
                    ecosystems=list(config.stack.packages.keys()),
                    max_results=settings.max_results_per_feed,
                    timeout_seconds=settings.request_timeout_seconds,
                    user_agent=settings.user_agent,
                )
            )
        )

    if config.feeds.msrc:
        feeds.append(
            MSRCFeed(
                MSRCSettings(
                    timeout_seconds=settings.request_timeout_seconds,
                    user_agent=settings.user_agent,
                )
            )
        )

    if config.feeds.cisa.enabled:
        feeds.append(
            CISAFeed(
                CISASettings(
                    timeout_seconds=settings.request_timeout_seconds,
                    user_agent=settings.user_agent,
                )
            )
        )

    if config.feeds.osv.enabled:
        feeds.append(
            OSVFeed(
                OSVSettings(
                    packages=config.stack.packages,
                    max_results=settings.max_results_per_feed,
                    timeout_seconds=settings.request_timeout_seconds,
                    user_agent=settings.user_agent,
                )
            )
        )

    if config.feeds.rss:
        sources = [RSSSource(name=item.name, url=item.url) for item in config.feeds.rss]
        feeds.append(
            RSSFeed(
                RSSSettings(
                    sources=sources,
                    timeout_seconds=settings.request_timeout_seconds,
                    user_agent=settings.user_agent,
                )
            )
        )

    if config.feeds.hackernews.enabled:
        terms = _build_hn_terms(config, config.feeds.hackernews.max_terms)
        feeds.append(
            HackerNewsFeed(
                HackerNewsSettings(
                    terms=terms,
                    max_results=settings.max_results_per_feed,
                    timeout_seconds=settings.request_timeout_seconds,
                    user_agent=settings.user_agent,
                )
            )
        )

    return feeds


def _init_config(target: Path) -> None:
    if target.exists():
        raise SystemExit(f"Config already exists at {target}")
    root = Path(__file__).resolve().parents[1]
    template = root / "config.example.yaml"
    if not template.exists():
        raise SystemExit("config.example.yaml not found")
    target.write_text(template.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Wrote config template to {target}")


def _build_hn_terms(config, max_terms: int) -> list[str]:
    terms: list[str] = []
    candidates = (
        config.stack.keywords
        + config.stack.services
        + config.stack.cloud
        + [pkg for packages in config.stack.packages.values() for pkg in packages]
        + config.stack.languages
    )
    for term in candidates:
        cleaned = term.strip()
        if len(cleaned) < 3:
            continue
        lowered = cleaned.lower()
        if lowered in terms:
            continue
        terms.append(lowered)
        if len(terms) >= max_terms:
            break
    return terms


def _build_dependency_graph(config, config_path: Path):
    deps = config.stack.deps
    deps_config = DependenciesConfig(
        enabled=deps.enabled,
        sources=[DependencySource(type=item.type, path=item.path) for item in deps.sources],
        include_transitive=deps.include_transitive,
        ecosystems=deps.ecosystems,
    )
    return load_dependency_graph(
        deps_config,
        base_dir=config_path.parent,
        normalize_names=config.stack.match.normalize_names,
    )


async def _poll_once(feeds, notifiers, config, state, dependencies, dry_run: bool) -> None:
    logger = logging.getLogger(__name__)
    since = state.last_poll

    tasks = [feed.fetch_recent(since=since) for feed in feeds]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    items = []
    for feed_result in results:
        if isinstance(feed_result, Exception):
            logger.error("Feed fetch failed: %s", feed_result)
            continue
        items.extend(feed_result)

    matched_count = 0
    notified_count = 0
    candidates = []
    for item in sorted(items, key=lambda x: _normalize_dt(x.published)):
        if was_sent(state, item.id):
            continue
        if not config.settings.include_low_severity and _is_low_severity(item):
            continue
        if _below_min_cvss(item, config.settings.min_cvss_score):
            continue

        match = calculate_relevance(item, config.stack, dependencies)
        if not match.is_relevant:
            continue

        matched_count += 1
        if dry_run:
            logger.info("[dry-run] Match: %s (%s)", item.id, "; ".join(match.reasons))
            mark_sent(state, item.id)
            continue

        score = score_alert(item, match, config.scoring, config.stack)
        message, metadata = build_notification_message(item, match.reasons, match, score)
        candidates.append((message, metadata, item))

    if not dry_run and candidates:
        candidates.sort(key=lambda entry: _priority_sort(entry[0].priority, entry[0].published))
        for message, metadata, item in candidates:
            if not notifiers:
                logger.warning("No notifier configured; skipping %s", item.id)
                continue
            sent = True
            for notifier in notifiers:
                try:
                    success = await notifier.send(message, metadata)
                except Exception as exc:
                    logger.error("Notifier failed for %s: %s", item.id, exc)
                    success = False
                sent = sent and success
            if sent:
                logger.info("Notified for %s", item.id)
                mark_sent(state, item.id)
                notified_count += 1
                if notified_count >= config.settings.max_notifications_per_run:
                    logger.warning(
                        "Reached max_notifications_per_run=%s; stopping early",
                        config.settings.max_notifications_per_run,
                    )
                    break

    state.last_poll = datetime.now(timezone.utc)
    prune_sent(state)
    if dry_run:
        logger.info("Dry-run complete: %s matches", matched_count)
    else:
        logger.info("Poll complete: %s matches, %s notified", matched_count, notified_count)


def _is_low_severity(item) -> bool:
    if item.cvss_score is None:
        return False
    return item.cvss_score < 4.0


def _below_min_cvss(item, min_score: float | None) -> bool:
    if min_score is None or item.cvss_score is None:
        return False
    return item.cvss_score < min_score


def _normalize_dt(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _priority_sort(priority: str, published: datetime) -> tuple[int, datetime]:
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    return (order.get(priority, 9), _normalize_dt(published))


def _build_test_item():
    from .feeds.base import FeedItem

    now = datetime.now(timezone.utc)
    return FeedItem(
        id=f"test:{int(now.timestamp())}",
        source="test",
        title="signl test alert: webhook verified",
        description="This is a synthetic test notification to verify your webhook.",
        url="https://github.com/heyosj/signl",
        published=now,
        severity="low",
        cvss_score=3.1,
        affected_packages=[],
        raw_data={},
    )


if __name__ == "__main__":
    asyncio.run(main())
