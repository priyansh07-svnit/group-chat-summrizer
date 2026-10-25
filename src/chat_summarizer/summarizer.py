"""Summarizer – chunks messages and queries Ollama for two-line summaries."""

from __future__ import annotations

from pathlib import Path

from chat_summarizer.config import AppConfig
from chat_summarizer.ollama_client import generate
from chat_summarizer.parsers.models import Message


def _load_prompt_template(config: AppConfig) -> str:
    """Read the user-editable prompt template from disk."""
    prompt_path = Path(config.summary.prompt_file)
    if not prompt_path.exists():
        # Fallback to a sensible inline default.
        return (
            "Summarize the following group chat in exactly two lines. "
            "If there are action items or dates mentioned, list them."
        )
    return prompt_path.read_text(encoding="utf-8").strip()


def _format_messages(messages: list[Message]) -> str:
    """Turn a list of messages into a single text block for the model."""
    return "\n".join(str(m) for m in messages)


def _chunk_messages(messages: list[Message], chunk_size: int) -> list[list[Message]]:
    """Split messages into chunks that stay under *chunk_size* characters.

    Each chunk is a contiguous slice of messages whose combined string
    representation doesn't exceed *chunk_size*.  This is character-based,
    which is a conservative proxy for tokens.
    """
    chunks: list[list[Message]] = []
    current_chunk: list[Message] = []
    current_len = 0

    for msg in messages:
        msg_len = len(str(msg))
        if current_chunk and current_len + msg_len > chunk_size:
            chunks.append(current_chunk)
            current_chunk = []
            current_len = 0
        current_chunk.append(msg)
        current_len += msg_len

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def summarize_messages(messages: list[Message], config: AppConfig) -> str:
    """Produce a two-line summary (with optional action items) for *messages*.

    If the messages exceed the configured chunk size, a **map-reduce**
    strategy is used:

    1. *Map*: summarize each chunk independently.
    2. *Reduce*: summarize the combined chunk summaries into a final output.

    Parameters
    ----------
    messages:
        The chat messages to summarize (should be pre-filtered for
        incremental processing).
    config:
        Application configuration (model, chunk size, prompt path, …).

    Returns
    -------
    str
        The model's summary text.
    """
    if not messages:
        return "No new messages to summarize."

    template = _load_prompt_template(config)
    chunks = _chunk_messages(messages, config.summary.chunk_size)

    if len(chunks) == 1:
        # Single-shot: everything fits in one prompt.
        chat_block = _format_messages(chunks[0])
        prompt = f"{template}\n\n---\nChat messages:\n{chat_block}\n---"
        return generate(prompt, config.ollama)

    # Map phase: summarize each chunk.
    chunk_summaries: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        chat_block = _format_messages(chunk)
        prompt = (
            f"{template}\n\n"
            f"(This is chunk {i} of {len(chunks)} from a long conversation.)\n\n"
            f"---\nChat messages:\n{chat_block}\n---"
        )
        summary = generate(prompt, config.ollama)
        chunk_summaries.append(summary)

    # Reduce phase: combine chunk summaries.
    combined = "\n\n".join(
        f"[Chunk {i}]\n{s}" for i, s in enumerate(chunk_summaries, 1)
    )
    reduce_prompt = (
        f"{template}\n\n"
        "Below are summaries of consecutive chunks from one long conversation. "
        "Combine them into a single final summary.\n\n"
        f"---\n{combined}\n---"
    )
    return generate(reduce_prompt, config.ollama)
