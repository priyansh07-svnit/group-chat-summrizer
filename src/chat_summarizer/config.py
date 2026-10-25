"""Configuration loader for group-chat-summarizer."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class OllamaConfig:
    """Ollama connection settings."""

    base_url: str = "http://localhost:11434"
    model: str = "qwen2.5:3b"
    timeout: int = 120


@dataclass
class SummaryConfig:
    """Summarization behaviour."""

    chunk_size: int = 3000
    prompt_file: str = "./prompts/summary.txt"


@dataclass
class WatchConfig:
    """Watch-mode settings."""

    interval_seconds: int = 300


@dataclass
class AppConfig:
    """Top-level application configuration."""

    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    summary: SummaryConfig = field(default_factory=SummaryConfig)
    watch: WatchConfig = field(default_factory=WatchConfig)
    chats_dir: str = "./chats"
    digests_dir: str = "./digests"


def _merge(defaults: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *overrides* into *defaults*."""
    merged = dict(defaults)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(config_path: str | Path | None = None) -> AppConfig:
    """Load configuration from a YAML file, falling back to defaults.

    Parameters
    ----------
    config_path:
        Path to a ``config.yaml`` file.  When *None* the loader looks for
        ``config.yaml`` in the current working directory.

    Returns
    -------
    AppConfig
        Fully resolved configuration dataclass.
    """
    raw: dict[str, Any] = {}

    if config_path is None:
        config_path = Path.cwd() / "config.yaml"
    else:
        config_path = Path(config_path)

    if config_path.exists():
        with open(config_path, encoding="utf-8") as fh:
            loaded = yaml.safe_load(fh)
            if isinstance(loaded, dict):
                raw = loaded

    ollama_raw = raw.get("ollama", {})
    summary_raw = raw.get("summary", {})
    watch_raw = raw.get("watch", {})

    return AppConfig(
        ollama=OllamaConfig(**{k: v for k, v in ollama_raw.items() if k in OllamaConfig.__dataclass_fields__}),
        summary=SummaryConfig(**{k: v for k, v in summary_raw.items() if k in SummaryConfig.__dataclass_fields__}),
        watch=WatchConfig(**{k: v for k, v in watch_raw.items() if k in WatchConfig.__dataclass_fields__}),
        chats_dir=raw.get("chats_dir", "./chats"),
        digests_dir=raw.get("digests_dir", "./digests"),
    )
