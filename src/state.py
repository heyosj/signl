from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import json
import os
from typing import Any


STATE_VERSION = 1


@dataclass
class State:
    last_poll: datetime | None
    sent_items: dict[str, datetime] = field(default_factory=dict)
    version: int = STATE_VERSION


def _parse_datetime(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def load_state(path: str) -> State:
    if not os.path.exists(path):
        return State(last_poll=None, sent_items={})

    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)

    if not isinstance(raw, dict):
        return State(last_poll=None, sent_items={})

    last_poll_raw = raw.get("last_poll")
    last_poll = _parse_datetime(last_poll_raw) if isinstance(last_poll_raw, str) else None

    sent_items = _parse_sent_items(raw.get("sent_items"))

    return State(last_poll=last_poll, sent_items=sent_items, version=int(raw.get("version", 1)))


def save_state(path: str, state: State) -> None:
    payload = {
        "version": state.version,
        "last_poll": _to_iso(state.last_poll) if state.last_poll else None,
        "sent_items": {item_id: _to_iso(ts) for item_id, ts in state.sent_items.items()},
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)


def mark_sent(state: State, item_id: str, timestamp: datetime | None = None) -> None:
    state.sent_items[item_id] = timestamp or datetime.now(timezone.utc)


def was_sent(state: State, item_id: str) -> bool:
    return item_id in state.sent_items


def prune_sent(state: State, days: int = 30) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    state.sent_items = {
        item_id: ts for item_id, ts in state.sent_items.items() if ts >= cutoff
    }


def _parse_sent_items(value: Any) -> dict[str, datetime]:
    now = datetime.now(timezone.utc)
    if value is None:
        return {}
    if isinstance(value, list):
        return {str(item_id): now for item_id in value}
    if isinstance(value, dict):
        parsed: dict[str, datetime] = {}
        for item_id, ts in value.items():
            if isinstance(ts, str):
                try:
                    parsed[str(item_id)] = _parse_datetime(ts)
                except ValueError:
                    parsed[str(item_id)] = now
            else:
                parsed[str(item_id)] = now
        return parsed
    return {}
