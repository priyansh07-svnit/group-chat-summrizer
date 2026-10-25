"""Incremental state tracking – remembers last-processed timestamp per chat."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

_STATE_FILE = ".state.json"


def _state_path(base_dir: str | Path) -> Path:
    """Return the path to the state file inside *base_dir*."""
    return Path(base_dir) / _STATE_FILE


def load_state(base_dir: str | Path) -> dict[str, str]:
    """Load the state dict mapping chat filename → last processed ISO timestamp.

    Returns an empty dict if the file doesn't exist yet.
    """
    p = _state_path(base_dir)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(base_dir: str | Path, state: dict[str, str]) -> None:
    """Persist the state dict to disk."""
    p = _state_path(base_dir)
    p.write_text(json.dumps(state, indent=2), encoding="utf-8")


def get_last_timestamp(state: dict[str, str], chat_name: str) -> datetime | None:
    """Return the last-processed timestamp for *chat_name*, or None."""
    iso = state.get(chat_name)
    if iso:
        try:
            return datetime.fromisoformat(iso)
        except ValueError:
            return None
    return None


def update_timestamp(state: dict[str, str], chat_name: str, ts: datetime) -> None:
    """Update the state in-memory (call :func:`save_state` to persist)."""
    state[chat_name] = ts.isoformat()
