# Security Stack News Notifier

## Project Overview

An open-source tool that monitors security feeds and notifies users only when items are relevant to their specific technology stack. Users define their environment (cloud providers, languages, packages, services) in a config file and receive Discord notifications for vulnerabilities, advisories, or security research that affects their stack.

**Core philosophy:** Minimal, robust, zero noise. If it doesn't apply to your stack, you don't hear about it.

## Scope and Non-Goals

**In scope (MVP):**
- Pull from a small set of public feeds.
- Match feed items to user-defined stack criteria.
- Notify via Discord webhook only when relevant.
- Keep local state to avoid duplicates.
- Simple CLI-driven operation (cron, Docker, systemd).

**Out of scope (MVP):**
- Web UI or multi-tenant hosting.
- Auto-discovery from package manifests.
- ML ranking or fuzzy relevance scoring.
- Rich dashboards or long-term storage.

## Goals

1. Parse a user-defined config file describing their technology stack.
2. Poll multiple security feeds on a configurable interval.
3. Match feed items against the user's stack configuration.
4. Send notifications via Discord webhook for relevant matches only.
5. Track previously sent notifications to avoid duplicates.
6. Be simple enough to self-host via cron, Docker, or systemd.

## Tech Stack

- **Language:** Python 3.11+
- **HTTP Client:** httpx (async)
- **Config Parsing:** PyYAML
- **No database:** use a local JSON file for state
- **No web framework:** CLI/background tool only

## Project Structure

```
/
├── config.example.yaml      # Template config users copy and modify
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point - orchestrates polling and notifications
│   ├── config.py            # Load and validate config.yaml
│   ├── feeds/
│   │   ├── __init__.py
│   │   ├── base.py          # Abstract base class for feeds
│   │   ├── nvd.py           # NVD/CVE feed
│   │   ├── github.py        # GitHub Security Advisories
│   │   └── msrc.py          # Microsoft Security Response Center
│   ├── matcher.py           # Logic to determine if a feed item is relevant
│   ├── notifiers/
│   │   ├── __init__.py
│   │   ├── base.py          # Abstract base class for notifiers
│   │   └── discord.py       # Discord webhook implementation
│   └── state.py             # Track sent notifications in a JSON file
├── Dockerfile
├── README.md
├── requirements.txt
└── .gitignore
```

## Configuration Schema

The user creates a `config.yaml` file:

```yaml
version: 1

stack:
  cloud:
    - azure
    - aws
    - gcp

  languages:
    - python
    - javascript
    - typescript
    - powershell
    - go

  packages:
    npm:
      - axios
      - react
      - lodash
      - express
    pip:
      - requests
      - django
      - flask
      - pydantic
      - azure-identity
    go:
      - gin
      - cobra

  services:
    - entra-id
    - intune
    - azure-sentinel
    - kubernetes
    - docker
    - postgresql
    - redis

  keywords:
    - kerberos
    - ntlm
    - active directory
    - oauth
    - saml

notifications:
  discord:
    webhook_url: "${DISCORD_WEBHOOK_URL}"

settings:
  poll_interval_minutes: 15
  state_file: "./state.json"
  include_low_severity: false
  max_results_per_feed: 200
  request_timeout_seconds: 20
  user_agent: "security-stack-notifier/0.1"
```

### Config Validation Rules

- `stack` keys are required; empty lists are allowed but discouraged.
- `packages` may omit ecosystems (treat as empty).
- `notifications.discord.webhook_url` is optional if `--dry-run` is used.
- `poll_interval_minutes` must be >= 5.
- `state_file` must be writable.
- Env var expansion should support `${VAR}` in any string.

### Data Model

```python
@dataclass
class StackConfig:
    cloud: list[str]
    languages: list[str]
    packages: dict[str, list[str]]  # ecosystem -> package names
    services: list[str]
    keywords: list[str]

@dataclass
class NotificationConfig:
    discord_webhook_url: str | None

@dataclass
class Settings:
    poll_interval_minutes: int
    state_file: str
    include_low_severity: bool
    max_results_per_feed: int
    request_timeout_seconds: int
    user_agent: str

@dataclass
class Config:
    stack: StackConfig
    notifications: NotificationConfig
    settings: Settings
```

## CLI

```
python -m src.main --config ./config.yaml [--once] [--dry-run] [--verbose]
```

- `--config PATH`: Path to config file (default: `./config.yaml`).
- `--once`: Run once and exit (for cron usage).
- `--dry-run`: Print matches but do not notify.
- `--verbose`: Set logging level to DEBUG.

## Feed Model

### feeds/base.py

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

@dataclass
class FeedItem:
    id: str                    # Unique identifier (CVE ID, advisory ID, etc.)
    source: str                # "nvd", "github", "msrc"
    title: str
    description: str
    url: str
    published: datetime
    severity: str | None       # "critical", "high", "medium", "low", or None
    cvss_score: float | None
    affected_packages: list[str]  # If known
    raw_data: dict             # Original payload for debugging

class BaseFeed(ABC):
    @abstractmethod
    async def fetch_recent(self, since: datetime | None = None) -> list[FeedItem]:
        """Fetch items published since the given datetime. If None, fetch last 24 hours."""
        pass
```

### Feed Normalization

- Normalize severities to `critical/high/medium/low` where possible.
- Keep `cvss_score` `None` if unavailable.
- Ensure `id` is globally unique (prefix with source if needed).

## Feed Implementations

### feeds/nvd.py

- Use NVD CVE API 2.0: `https://services.nvd.nist.gov/rest/json/cves/2.0`.
- Query params: `pubStartDate`, `pubEndDate` (ISO 8601 format).
- Respect rate limits; add delay between pages (min 1 second).
- Parse CVE ID, description, CVSS v3.1 score, references.
- Extract affected CPE entries and map to package names when possible.
- Note: CPE to package matching is lossy; rely on text matching as fallback.

### feeds/github.py

- Use GitHub Security Advisories REST API: `https://api.github.com/advisories`.
- Filter by ecosystem list derived from `stack.packages` keys.
- No auth required for public advisories; rate limits apply.
- Extract: GHSA ID, summary, severity, vulnerable package + versions, CVE if linked.

### feeds/msrc.py

- Use MSRC CVRF API: `https://api.msrc.microsoft.com/cvrf/v2.0/cvrf` or RSS feed.
- Focus on Azure, Windows, Office, and Entra ID related bulletins.
- Extract: KB numbers, affected products, severity, CVE references.
- Prefer RSS for simplicity unless CVRF provides richer data.

## Matching Logic

```python
def calculate_relevance(item: FeedItem, config: StackConfig) -> tuple[bool, list[str]]:
    """
    Returns (is_relevant, list of reasons why it matched).

    Matching priority:
    1. Direct package name match (highest confidence)
    2. Service name match
    3. Keyword match
    4. Language match (only if specific to that language)
    5. Cloud provider match (only if specific service mentioned)
    """
    reasons = []
    text = f"{item.title} {item.description}".lower()

    # Check affected_packages field directly if available
    for ecosystem, packages in config.packages.items():
        for pkg in packages:
            if pkg.lower() in [p.lower() for p in item.affected_packages]:
                reasons.append(f"Direct package match: {pkg}")

    # Check text content for package names
    for ecosystem, packages in config.packages.items():
        for pkg in packages:
            if pkg.lower() in text:
                reasons.append(f"Package mentioned: {pkg}")

    # Check services
    for service in config.services:
        if service.lower() in text:
            reasons.append(f"Service match: {service}")

    # Check keywords
    for keyword in config.keywords:
        if keyword.lower() in text:
            reasons.append(f"Keyword match: {keyword}")

    # Deduplicate reasons
    reasons = list(set(reasons))

    return (len(reasons) > 0, reasons)
```

### Matching Notes

- Case-insensitive matching.
- Consider word boundaries for short tokens (e.g., `go`, `sql`).
- Allow configuration to add `stop_words` later if false positives show up.
- If `include_low_severity` is false, drop `cvss_score < 4.0` when available.

## Notifiers

### notifiers/base.py

```python
from abc import ABC, abstractmethod

class BaseNotifier(ABC):
    @abstractmethod
    async def send(self, item: FeedItem, reasons: list[str]) -> bool:
        """Send notification. Returns True if successful."""
        pass
```

### notifiers/discord.py

- POST to webhook URL.
- Format message as an embed with:
  - Title: Item title
  - Description: Truncated description + reasons for match
  - Color: Based on severity (red = critical, orange = high, yellow = medium, gray = low)
  - Fields: Source, CVSS score, affected packages
  - URL button to the advisory
- Handle rate limits (429) with backoff.

Example embed structure:
```json
{
  "embeds": [{
    "title": "CVE-2024-XXXXX: Critical vulnerability in lodash",
    "description": "Prototype pollution vulnerability allowing remote code execution...",
    "url": "https://nvd.nist.gov/vuln/detail/CVE-2024-XXXXX",
    "color": 15158332,
    "fields": [
      {"name": "Severity", "value": "Critical (9.8)", "inline": true},
      {"name": "Source", "value": "NVD", "inline": true},
      {"name": "Why you're seeing this", "value": "Package match: lodash", "inline": false}
    ],
    "timestamp": "2024-01-15T12:00:00Z"
  }]
}
```

## State Management

```python
@dataclass
class State:
    last_poll: datetime
    sent_items: set[str]  # Set of item IDs that have been notified

    version: int = 1
```

State file format:
```json
{
  "version": 1,
  "last_poll": "2024-01-15T12:00:00Z",
  "sent_items": ["CVE-2024-1234", "GHSA-xxxx-yyyy"]
}
```

### State Functions

```python
def load_state(path: str) -> State:
    """Load state from JSON file. Create default if doesn't exist."""
    pass

def save_state(path: str, state: State) -> None:
    """Save state to JSON file."""
    pass

def mark_sent(state: State, item_id: str) -> None:
    """Mark an item as sent."""
    pass

def was_sent(state: State, item_id: str) -> bool:
    """Check if an item was already sent."""
    pass
```

### Pruning

- Remove items older than 30 days from `sent_items` to prevent unbounded growth.
- Keep a secondary map of `item_id -> first_seen` if needed for pruning.

## main.py

```python
import asyncio
import argparse

async def main():
    # 1. Parse CLI args (--config path, --once flag)
    # 2. Load config
    # 3. Load state
    # 4. Initialize feeds and notifiers
    # 5. Loop:
    #    a. Fetch from all feeds (concurrently)
    #    b. For each item not in sent_items:
    #       - Check relevance
    #       - If relevant, send notification
    #       - Mark as sent
    #    c. Save state
    #    d. Sleep for poll_interval (unless --once)
    pass

if __name__ == "__main__":
    asyncio.run(main())
```

### Concurrency

- Use `asyncio.gather` to fetch feeds in parallel.
- Use a per-feed semaphore to limit concurrent requests.

## Error Handling

- Network failures: Log and continue, do not crash.
- Invalid config: Fail fast with a clear error message.
- Webhook failures: Retry with exponential backoff (max 3 attempts).
- Rate limits: Respect retry-after headers, add delays.
- Malformed feed data: Log warning, skip item, continue.

## Logging

Use Python's logging module:
- INFO: Successful polls, notifications sent.
- WARNING: Skipped items, rate limits hit.
- ERROR: Failed requests, webhook failures.
- DEBUG: Full item details, matching logic.

Default to INFO level, configurable via `--verbose`.

## Security and Privacy

- Do not log webhook URLs or secrets.
- Avoid storing full raw feed payloads in state; store minimal identifiers.
- Use a descriptive User-Agent to avoid being blocked by feeds.

## Testing (MVP)

- Unit tests for config loading and env expansion.
- Unit tests for matching logic (positive/negative cases).
- Small integration test for one feed with mocked HTTP response.

## Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY config.example.yaml .

# Config should be mounted at runtime
# docker run -v ./config.yaml:/app/config.yaml -v ./state.json:/app/state.json

CMD ["python", "-m", "src.main"]
```

## README.md Content

Include:
1. One-line description.
2. Quick start (copy config, edit, run).
3. Configuration reference.
4. Deployment options (cron, Docker, systemd).
5. Adding custom feeds (extending BaseFeed).
6. Adding notification channels (extending BaseNotifier).
7. Contributing guidelines.
8. License (MIT).

## Implementation Priority

Build in this order:

1. **config.py** - Get config loading working.
2. **state.py** - Simple JSON state management.
3. **feeds/base.py + feeds/nvd.py** - One working feed.
4. **matcher.py** - Basic relevance matching.
5. **notifiers/base.py + notifiers/discord.py** - Discord notifications.
6. **main.py** - Wire it all together.
7. **Test end-to-end with real config.**
8. **feeds/github.py** - Second feed.
9. **feeds/msrc.py** - Third feed.
10. **Dockerfile + README.**

## Future Enhancements

- Slack notifier.
- Email notifier.
- Web UI for config management.
- Hosted multi-tenant version.
- Auto-discovery from package manifests.
- ML-based relevance scoring.
- RSS feed output.
