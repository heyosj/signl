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

See `config.example.yaml` for a simplified starter config. Key sections:
- `mode`: quiet/normal/loud alerting behavior
- `always_page`: keywords that always page when relevant
- `version`: config schema version (default: 1)
- `stack`: cloud, languages, packages, services, keywords, deps, match
- `notify`: list of notifiers (Slack/Discord/webhook)
- `notifications.slack.webhook_url` + `notifications.discord.webhook_url`: legacy single notifier config
- `feeds`: enable/disable sources and RSS lists
- Feed sources can be disabled by setting the `feeds.*` flag to `false`.
- `settings`: poll interval, state file path, timeouts, user agent, max notifications per run, min CVSS score
- `scoring`: weights, thresholds, keywords, preferred sources

### Example (legacy, still supported)

```
notifications:
  slack:
    webhook_url: "${SLACK_WEBHOOK_URL}"
```

### Example (multi-notifier)

```
notify:
  - type: slack
    webhook_url: "${SLACK_WEBHOOK_URL}"
  - type: discord
    webhook_url: "${DISCORD_WEBHOOK_URL}"
  - type: webhook
    url: "${WEBHOOK_URL}"
    headers:
      Authorization: "Bearer ${WEBHOOK_TOKEN}"
```

### Dependency Matching

`stack.deps` can augment `stack.packages` with direct and transitive dependencies.

Supported sources:
- npm: `package.json` (direct), `package-lock.json` (transitive)
- pip: `requirements.txt` (direct), `poetry.lock` (transitive)

Matching defaults to `loose` mode (aliases + normalization). Set `stack.match.mode: strict` for exact-only matches.

### Scoring / Priority

Each matched alert gets a score (0-100) and priority (P0-P3). Defaults weight:
- Severity (CVSS or vendor mapping)
- Exploitability signals (CISA KEV, keywords)
- Relevance strength (direct > transitive > service/cloud/keyword)
- Recency

Notifications include priority, score, and the top scoring rationale.
Alerts are sent grouped by priority (P0 first).

### Webhook Payload

Generic webhook receives JSON with:
`title`, `summary`, `priority`, `score`, `url`, `source`, `published`, `affected`, `tags`, `reasons`, `rationale`.

### Migration Notes

- `notifications.*` is still accepted, but `notify` is preferred for multiple outputs.
- Existing configs continue to work as-is; new fields are optional.
- If `mode` is omitted, signl preserves legacy behavior and pages any relevant alert.

### Noise Control

Minimal config (opinionated defaults, no rule tuning):

```
mode: quiet

stack:
  cloud: [azure]
  services: [kubernetes]
  packages:
    npm: [axios]

always_page:
  - trufflehog

notify:
  - type: slack
    webhook_url: "${SLACK_WEBHOOK_URL}"
```

Quiet mode only pages for relevant, high-confidence exploitation signals. The `always_page` list bypasses mode when the term appears in a relevant alert. Everything else is routed to the digest.

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
