"""Tests for incremental state tracking."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from chat_summarizer.state import (
    get_last_timestamp,
    load_state,
    save_state,
    update_timestamp,
)


class TestState:
    """Tests for state load / save / update cycle."""

    def test_empty_state_when_no_file(self, tmp_path: Path) -> None:
        state = load_state(tmp_path)
        assert state == {}

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        state = {"chat.txt": "2024-01-15T10:30:00"}
        save_state(tmp_path, state)

        loaded = load_state(tmp_path)
        assert loaded == state

    def test_get_last_timestamp_present(self) -> None:
        state = {"chat.txt": "2024-01-15T10:30:00"}
        ts = get_last_timestamp(state, "chat.txt")
        assert ts == datetime(2024, 1, 15, 10, 30)

    def test_get_last_timestamp_missing(self) -> None:
        state = {}
        ts = get_last_timestamp(state, "chat.txt")
        assert ts is None

    def test_update_timestamp(self) -> None:
        state: dict[str, str] = {}
        dt = datetime(2024, 6, 1, 12, 0)
        update_timestamp(state, "chat.txt", dt)
        assert state["chat.txt"] == dt.isoformat()

    def test_corrupt_state_file(self, tmp_path: Path) -> None:
        """A corrupt JSON file should be handled gracefully."""
        (tmp_path / ".state.json").write_text("NOT JSON!!!", encoding="utf-8")
        state = load_state(tmp_path)
        assert state == {}
