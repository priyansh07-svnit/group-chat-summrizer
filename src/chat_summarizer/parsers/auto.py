"""Auto-detect chat format and parse accordingly."""

from __future__ import annotations

from pathlib import Path

from chat_summarizer.parsers.models import Message
from chat_summarizer.parsers.telegram import parse_telegram
from chat_summarizer.parsers.whatsapp import parse_whatsapp


def parse_file(path: str | Path) -> list[Message]:
    """Detect the file format and return parsed messages.

    * Files ending in ``.json`` → Telegram parser
    * Files ending in ``.txt`` → WhatsApp parser
    * Other extensions → raises ``ValueError``

    Parameters
    ----------
    path:
        Path to the chat export file.

    Returns
    -------
    list[Message]
        Parsed and sorted messages.

    Raises
    ------
    ValueError
        If the file extension is unsupported.
    """
    path = Path(path)
    ext = path.suffix.lower()

    if ext == ".json":
        return parse_telegram(path)
    elif ext == ".txt":
        return parse_whatsapp(path)
    else:
        raise ValueError(
            f"Unsupported file format '{ext}'. "
            "Expected .txt (WhatsApp) or .json (Telegram)."
        )
