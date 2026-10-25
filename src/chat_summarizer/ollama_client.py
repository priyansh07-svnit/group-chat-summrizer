"""Minimal Ollama HTTP client – localhost only."""

from __future__ import annotations

from urllib.parse import urlparse

import requests

from chat_summarizer.config import OllamaConfig


class OllamaError(RuntimeError):
    """Raised when Ollama returns an error or is unreachable."""


def _assert_localhost(url: str) -> None:
    """Raise if *url* doesn't point to localhost.

    This is the privacy guard: the summarizer must never phone home.
    """
    parsed = urlparse(url)
    host = parsed.hostname or ""
    if host not in ("localhost", "127.0.0.1", "::1"):
        raise OllamaError(
            f"Refusing to connect to non-localhost URL: {url!r}. "
            "group-chat-summarizer only talks to a local Ollama instance."
        )


def generate(prompt: str, config: OllamaConfig) -> str:
    """Send a prompt to the Ollama ``/api/generate`` endpoint.

    Parameters
    ----------
    prompt:
        The full prompt (system + user text) to send.
    config:
        Ollama connection settings.

    Returns
    -------
    str
        The model's generated text.

    Raises
    ------
    OllamaError
        On connection failure or non-200 response.
    """
    url = f"{config.base_url.rstrip('/')}/api/generate"
    _assert_localhost(url)

    payload = {
        "model": config.model,
        "prompt": prompt,
        "stream": False,
    }

    try:
        resp = requests.post(url, json=payload, timeout=config.timeout)
    except requests.ConnectionError:
        raise OllamaError(
            f"Cannot reach Ollama at {config.base_url}. "
            "Is it running?  Start it with: ollama serve"
        )
    except requests.Timeout:
        raise OllamaError(
            f"Ollama request timed out after {config.timeout}s. "
            "Try a smaller model or increase timeout in config.yaml."
        )

    if resp.status_code != 200:
        raise OllamaError(
            f"Ollama returned HTTP {resp.status_code}: {resp.text[:300]}"
        )

    data = resp.json()
    return data.get("response", "").strip()


def check_health(config: OllamaConfig) -> tuple[bool, str]:
    """Check that Ollama is reachable and the configured model is available.

    Returns
    -------
    tuple[bool, str]
        ``(ok, message)`` where *ok* is True when everything looks good.
    """
    _assert_localhost(config.base_url)

    # 1. Can we reach Ollama at all?
    try:
        resp = requests.get(
            f"{config.base_url.rstrip('/')}/api/tags",
            timeout=5,
        )
    except requests.ConnectionError:
        return False, (
            f"Cannot reach Ollama at {config.base_url}.\n"
            "  -> Install: https://ollama.com/download\n"
            "  -> Then run: ollama serve"
        )
    except requests.Timeout:
        return False, f"Ollama at {config.base_url} is not responding (timeout)."

    if resp.status_code != 200:
        return False, f"Ollama returned HTTP {resp.status_code}."

    # 2. Is the model pulled?
    data = resp.json()
    available_models = [m.get("name", "") for m in data.get("models", [])]
    # Ollama may list model names with or without a tag
    model_name = config.model
    found = any(
        model_name == m or model_name == m.split(":")[0] or m.startswith(model_name)
        for m in available_models
    )
    if not found:
        return False, (
            f"Model '{model_name}' is not pulled.\n"
            f"  -> Run: ollama pull {model_name}\n"
            f"  Available models: {', '.join(available_models) or '(none)'}"
        )

    return True, f"Ollama is running and model '{model_name}' is ready."
