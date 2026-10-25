"""Parser for WhatsApp exported .txt chat files.

WhatsApp exports have lines like:
    12/25/23, 14:05 - Alice: Happy holidays!
    1/5/24, 09:30 - Bob: Thanks!

Multi-line messages continue on the next line without the date prefix.
System messages (e.g. "Alice added Bob") lack the ": " after the sender.
Media placeholders like "<Media omitted>" are skipped.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from chat_summarizer.parsers.models import Message

# Matches the beginning of a WhatsApp message line.
# Group 1: date+time, Group 2: sender, Group 3: first line of text.
_LINE_RE = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)"  # timestamp
    r"\s*[-–]\s*"                                                                    # separator
    r"([^:]+):\s"                                                                    # sender
    r"(.*)$"                                                                          # text
)

_MEDIA_PLACEHOLDER = re.compile(
    r"<Media omitted>|image omitted|video omitted|audio omitted|sticker omitted|GIF omitted|document omitted|Contact card omitted",
    re.IGNORECASE,
)

# Common date formats WhatsApp uses across locales.
_DATE_FORMATS = [
    "%m/%d/%y, %H:%M",
    "%m/%d/%Y, %H:%M",
    "%d/%m/%y, %H:%M",
    "%d/%m/%Y, %H:%M",
    "%m/%d/%y, %I:%M %p",
    "%m/%d/%Y, %I:%M %p",
    "%d/%m/%y, %I:%M %p",
    "%d/%m/%Y, %I:%M %p",
    "%m/%d/%y, %H:%M:%S",
    "%m/%d/%Y, %H:%M:%S",
]


def _parse_timestamp(raw: str) -> datetime | None:
    """Try multiple date formats and return the first match."""
    raw = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def parse_whatsapp(path: str | Path) -> list[Message]:
    """Parse a WhatsApp exported .txt file into a list of :class:`Message`.

    Parameters
    ----------
    path:
        Path to the exported ``.txt`` file.

    Returns
    -------
    list[Message]
        Parsed messages sorted by timestamp, with media placeholders and
        system messages removed.
    """
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    messages: list[Message] = []
    current_ts: datetime | None = None
    current_sender: str | None = None
    current_text_parts: list[str] = []

    def _flush() -> None:
        if current_ts and current_sender and current_text_parts:
            full_text = "\n".join(current_text_parts).strip()
            if full_text and not _MEDIA_PLACEHOLDER.search(full_text):
                messages.append(Message(timestamp=current_ts, sender=current_sender, text=full_text))

    for line in lines:
        m = _LINE_RE.match(line)
        if m:
            _flush()
            ts = _parse_timestamp(m.group(1))
            if ts is None:
                # Can't parse date – treat as continuation.
                current_text_parts.append(line)
                continue
            current_ts = ts
            current_sender = m.group(2).strip()
            current_text_parts = [m.group(3)]
        else:
            # Continuation of the previous message.
            current_text_parts.append(line)

    _flush()
    return sorted(messages, key=lambda m: m.timestamp)
