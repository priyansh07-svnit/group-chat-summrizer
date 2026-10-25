"""Tests for WhatsApp and Telegram parsers."""

from __future__ import annotations

import json
import textwrap
from datetime import datetime
from pathlib import Path

import pytest

from chat_summarizer.parsers import Message, parse_file, parse_telegram, parse_whatsapp


# ── WhatsApp ────────────────────────────────────────────────────────────────


class TestWhatsAppParser:
    """Tests for the WhatsApp .txt parser."""

    def test_basic_messages(self, tmp_path: Path) -> None:
        content = textwrap.dedent("""\
            1/15/24, 10:30 - Alice: Hello everyone!
            1/15/24, 10:32 - Bob: Hi Alice!
            1/15/24, 10:35 - Charlie: Hey there
        """)
        f = tmp_path / "chat.txt"
        f.write_text(content, encoding="utf-8")

        messages = parse_whatsapp(f)

        assert len(messages) == 3
        assert messages[0].sender == "Alice"
        assert messages[0].text == "Hello everyone!"
        assert messages[1].sender == "Bob"
        assert messages[2].sender == "Charlie"

    def test_media_omitted_skipped(self, tmp_path: Path) -> None:
        content = textwrap.dedent("""\
            1/15/24, 10:30 - Alice: Hello!
            1/15/24, 10:31 - Bob: <Media omitted>
            1/15/24, 10:32 - Charlie: Nice photo!
        """)
        f = tmp_path / "chat.txt"
        f.write_text(content, encoding="utf-8")

        messages = parse_whatsapp(f)

        assert len(messages) == 2
        senders = [m.sender for m in messages]
        assert "Bob" not in senders

    def test_system_messages_skipped(self, tmp_path: Path) -> None:
        """System messages lack the ': ' pattern, so they shouldn't parse."""
        content = textwrap.dedent("""\
            1/15/24, 10:30 - Alice added Bob
            1/15/24, 10:31 - Alice: Hey Bob!
        """)
        f = tmp_path / "chat.txt"
        f.write_text(content, encoding="utf-8")

        messages = parse_whatsapp(f)

        assert len(messages) == 1
        assert messages[0].sender == "Alice"

    def test_multiline_message(self, tmp_path: Path) -> None:
        content = textwrap.dedent("""\
            1/15/24, 10:30 - Alice: This is line one
            and this is line two
            1/15/24, 10:32 - Bob: Short message
        """)
        f = tmp_path / "chat.txt"
        f.write_text(content, encoding="utf-8")

        messages = parse_whatsapp(f)

        assert len(messages) == 2
        assert "line one\nand this is line two" in messages[0].text

    def test_sorted_by_timestamp(self, tmp_path: Path) -> None:
        content = textwrap.dedent("""\
            1/15/24, 14:00 - Bob: Afternoon
            1/15/24, 09:00 - Alice: Morning
        """)
        f = tmp_path / "chat.txt"
        f.write_text(content, encoding="utf-8")

        messages = parse_whatsapp(f)

        assert messages[0].sender == "Alice"
        assert messages[1].sender == "Bob"

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")

        messages = parse_whatsapp(f)
        assert messages == []


# ── Telegram ────────────────────────────────────────────────────────────────


class TestTelegramParser:
    """Tests for the Telegram JSON parser."""

    def _write_json(self, tmp_path: Path, messages: list) -> Path:
        data = {"name": "Test Group", "type": "personal_chat", "messages": messages}
        f = tmp_path / "result.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        return f

    def test_basic_messages(self, tmp_path: Path) -> None:
        f = self._write_json(tmp_path, [
            {"id": 1, "type": "message", "date": "2024-01-20T09:00:00", "from": "Alice", "text": "Hello!"},
            {"id": 2, "type": "message", "date": "2024-01-20T09:05:00", "from": "Bob", "text": "Hi!"},
        ])

        messages = parse_telegram(f)

        assert len(messages) == 2
        assert messages[0].sender == "Alice"
        assert messages[1].sender == "Bob"

    def test_service_messages_skipped(self, tmp_path: Path) -> None:
        f = self._write_json(tmp_path, [
            {"id": 1, "type": "message", "date": "2024-01-20T09:00:00", "from": "Alice", "text": "Hello!"},
            {"id": 2, "type": "service", "date": "2024-01-20T09:01:00", "actor": "Alice", "text": "Alice pinned a message"},
        ])

        messages = parse_telegram(f)

        assert len(messages) == 1

    def test_rich_text_flattened(self, tmp_path: Path) -> None:
        f = self._write_json(tmp_path, [
            {
                "id": 1, "type": "message", "date": "2024-01-20T09:00:00",
                "from": "Lena",
                "text": ["Check this: ", {"type": "bold", "text": "important"}, " stuff"],
            },
        ])

        messages = parse_telegram(f)

        assert len(messages) == 1
        assert messages[0].text == "Check this: important stuff"

    def test_media_only_skipped(self, tmp_path: Path) -> None:
        f = self._write_json(tmp_path, [
            {"id": 1, "type": "message", "date": "2024-01-20T09:00:00", "from": "Sam", "photo": "x.jpg", "text": ""},
            {"id": 2, "type": "message", "date": "2024-01-20T09:05:00", "from": "Sam", "text": "Caption!"},
        ])

        messages = parse_telegram(f)

        assert len(messages) == 1
        assert messages[0].text == "Caption!"

    def test_empty_messages(self, tmp_path: Path) -> None:
        f = self._write_json(tmp_path, [])
        messages = parse_telegram(f)
        assert messages == []


# ── Auto-detect ─────────────────────────────────────────────────────────────


class TestAutoDetect:
    """Tests for format auto-detection."""

    def test_txt_routed_to_whatsapp(self, tmp_path: Path) -> None:
        f = tmp_path / "chat.txt"
        f.write_text("1/15/24, 10:30 - Alice: Hello!\n", encoding="utf-8")

        messages = parse_file(f)
        assert len(messages) == 1

    def test_json_routed_to_telegram(self, tmp_path: Path) -> None:
        f = tmp_path / "chat.json"
        data = {"messages": [
            {"id": 1, "type": "message", "date": "2024-01-20T09:00:00", "from": "A", "text": "Hi"},
        ]}
        f.write_text(json.dumps(data), encoding="utf-8")

        messages = parse_file(f)
        assert len(messages) == 1

    def test_unsupported_format_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "chat.csv"
        f.write_text("a,b,c", encoding="utf-8")

        with pytest.raises(ValueError, match="Unsupported"):
            parse_file(f)
