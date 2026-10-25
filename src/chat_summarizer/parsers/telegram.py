"""Parser for Telegram exported JSON files.

Telegram's "Export chat history" (JSON) produces a ``result.json`` with::

    {
      "name": "Group Name",
      "type": "...",
      "messages": [
        {
          "id": 1,
          "type": "message",
          "date": "2024-01-15T10:30:00",
          "from": "Alice",
          "text": "Hello!"
        },
        ...
      ]
    }

The ``text`` field can be a plain string **or** a list of mixed objects
(plain strings and dicts with ``type``/``text`` keys for formatting).  We
flatten these into a single string and skip service messages and media-only
messages.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from chat_summarizer.parsers.models import Message


def _flatten_text(text_field: str | list[Any]) -> str:
    """Convert Telegram's text field (string or rich list) to plain text."""
    if isinstance(text_field, str):
        return text_field
    parts: list[str] = []
    for part in text_field:
        if isinstance(part, str):
            parts.append(part)
        elif isinstance(part, dict):
            parts.append(part.get("text", ""))
    return "".join(parts)


def parse_telegram(path: str | Path) -> list[Message]:
    """Parse a Telegram exported JSON file into a list of :class:`Message`.

    Parameters
    ----------
    path:
        Path to the ``result.json`` file.

    Returns
    -------
    list[Message]
        Parsed messages sorted by timestamp, skipping service/media messages.
    """
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))

    raw_messages: list[dict[str, Any]] = data.get("messages", [])
    messages: list[Message] = []

    for entry in raw_messages:
        # Skip non-message types (service messages, etc.)
        if entry.get("type") != "message":
            continue

        # Skip media-only messages (photo, video, sticker, etc.)
        if "photo" in entry or "file" in entry or "sticker_emoji" in entry:
            text_field = entry.get("text", "")
            flat = _flatten_text(text_field).strip()
            if not flat:
                continue
        else:
            text_field = entry.get("text", "")
            flat = _flatten_text(text_field).strip()
            if not flat:
                continue

        sender = entry.get("from", entry.get("actor", "Unknown"))
        if not sender:
            sender = "Unknown"

        date_str = entry.get("date", "")
        try:
            ts = datetime.fromisoformat(date_str)
        except (ValueError, TypeError):
            continue

        messages.append(Message(timestamp=ts, sender=sender, text=flat))

    return sorted(messages, key=lambda m: m.timestamp)
