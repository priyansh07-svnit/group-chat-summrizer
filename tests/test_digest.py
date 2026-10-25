"""Tests for the digest writer."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from chat_summarizer.digest import write_digest


class TestDigest:
    """Tests for Markdown digest generation."""

    def test_creates_digest_file(self, tmp_path: Path) -> None:
        summaries = {"chat.txt": "Summary:\nLine 1\nLine 2"}
        today = date(2024, 1, 15)

        path = write_digest(summaries, tmp_path, today=today)

        assert path.exists()
        assert path.name == "2024-01-15.md"
        content = path.read_text(encoding="utf-8")
        assert "Line 1" in content
        assert "Line 2" in content

    def test_creates_digests_directory(self, tmp_path: Path) -> None:
        target = tmp_path / "sub" / "digests"
        write_digest({"a.txt": "test"}, target, today=date(2024, 1, 1))
        assert target.exists()

    def test_multiple_chats_sorted(self, tmp_path: Path) -> None:
        summaries = {
            "z_chat.txt": "Z summary",
            "a_chat.txt": "A summary",
        }
        path = write_digest(summaries, tmp_path, today=date(2024, 6, 1))
        content = path.read_text(encoding="utf-8")
        # "A Chat" should appear before "Z Chat".
        assert content.index("A Chat") < content.index("Z Chat")

    def test_empty_summaries(self, tmp_path: Path) -> None:
        path = write_digest({}, tmp_path, today=date(2024, 1, 1))
        content = path.read_text(encoding="utf-8")
        assert "Chat Digest" in content
