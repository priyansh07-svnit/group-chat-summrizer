"""Shared data model for parsed chat messages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Message:
    """A single chat message.

    Attributes
    ----------
    timestamp : datetime
        When the message was sent.
    sender : str
        Display name of the sender.
    text : str
        Plain-text body of the message.
    """

    timestamp: datetime
    sender: str
    text: str

    def __str__(self) -> str:
        ts = self.timestamp.strftime("%Y-%m-%d %H:%M")
        return f"[{ts}] {self.sender}: {self.text}"
