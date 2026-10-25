"""Tests for the chunking logic in summarizer.py."""

from __future__ import annotations

from datetime import datetime

from chat_summarizer.parsers.models import Message
from chat_summarizer.summarizer import _chunk_messages


def _msg(text: str, minute: int = 0) -> Message:
    """Helper to create a Message with minimal boilerplate."""
    return Message(
        timestamp=datetime(2024, 1, 15, 10, minute),
        sender="Test",
        text=text,
    )


class TestChunking:
    """Tests for the _chunk_messages helper."""

    def test_single_chunk_when_small(self) -> None:
        msgs = [_msg("hi", i) for i in range(3)]
        chunks = _chunk_messages(msgs, chunk_size=10_000)
        assert len(chunks) == 1
        assert len(chunks[0]) == 3

    def test_multiple_chunks_when_large(self) -> None:
        # Each message ~30 chars as string repr; 10 messages ~300 chars.
        msgs = [_msg(f"message number {i:03d}", i) for i in range(10)]
        chunks = _chunk_messages(msgs, chunk_size=100)
        assert len(chunks) > 1
        # All messages accounted for.
        total = sum(len(c) for c in chunks)
        assert total == 10

    def test_empty_input(self) -> None:
        chunks = _chunk_messages([], chunk_size=1000)
        assert chunks == []

    def test_single_large_message(self) -> None:
        """A single message larger than chunk_size should still be in one chunk."""
        msgs = [_msg("x" * 5000)]
        chunks = _chunk_messages(msgs, chunk_size=100)
        assert len(chunks) == 1
        assert len(chunks[0]) == 1
