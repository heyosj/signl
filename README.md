# Security Stack News Notifier

Minimal, stack-aware security feed monitor that only notifies you when advisories match your tech stack.

Sources included (free):
- NVD CVE API
- GitHub Security Advisories
- MSRC RSS
- CISA KEV catalog
- OSV.dev
- Hacker News (Algolia)
- Custom RSS feeds (security blogs, distro advisories)

## Quick Start

1. Copy and edit the config:

```
python -m src.main --init-config --config ./config.yaml
```

2. Set your Discord webhook:

```
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
```

3. Install and run:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.main --config ./config.yaml --once
```

## Configuration

See `config.example.yaml` for the full schema. Key sections:
- `stack`: cloud, languages, packages, services, keywords
- `notifications.slack.webhook_url`: Slack webhook (primary)
- `notifications.discord.webhook_url`: Discord webhook (testing/optional)
- `feeds`: enable/disable sources and RSS lists
- Feed sources can be disabled by setting the `feeds.*` flag to `false`.
- `settings`: poll interval, state file path, timeouts, user agent

## Deployment

- Cron: run with `--once` every N minutes.
- Docker: mount `config.yaml` and `state.json` into `/app`.
- systemd: run `python -m src.main` as a service.

## Troubleshooting

- No alerts: delete `state.json` to re-scan the last 24 hours.
- GitHub rate limit: set `GITHUB_TOKEN` or disable the GitHub feed.
- PEP 668 error: use a virtual environment before `pip install`.

## Extending Feeds

Implement a new feed by extending `BaseFeed` in `src/feeds/base.py` and returning normalized `FeedItem` objects.

## Extending Notifiers

Implement a new notifier by extending `BaseNotifier` in `src/notifiers/base.py`.

## Contributing

Small PRs welcome: keep matching rules conservative and avoid noisy alerts.

## License

MIT
