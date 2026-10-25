"""Tests for the Ollama client – mocked, no real server needed."""

from __future__ import annotations

import pytest
import requests

from chat_summarizer.config import OllamaConfig
from chat_summarizer.ollama_client import OllamaError, _assert_localhost, check_health, generate


class TestLocalhostGuard:
    """The privacy guard must reject any non-localhost URL."""

    def test_localhost_allowed(self) -> None:
        _assert_localhost("http://localhost:11434")

    def test_127_allowed(self) -> None:
        _assert_localhost("http://127.0.0.1:11434")

    def test_remote_rejected(self) -> None:
        with pytest.raises(OllamaError, match="non-localhost"):
            _assert_localhost("https://api.openai.com/v1")

    def test_other_host_rejected(self) -> None:
        with pytest.raises(OllamaError, match="non-localhost"):
            _assert_localhost("http://192.168.1.100:11434")


class TestGenerate:
    """Tests for the generate() function with mocked HTTP."""

    def test_successful_generation(self, mocker) -> None:
        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "Summary:\nLine one.\nLine two."}
        mocker.patch("chat_summarizer.ollama_client.requests.post", return_value=mock_resp)

        config = OllamaConfig()
        result = generate("Summarize this chat", config)

        assert "Line one" in result
        assert "Line two" in result

    def test_connection_error(self, mocker) -> None:
        mocker.patch(
            "chat_summarizer.ollama_client.requests.post",
            side_effect=requests.ConnectionError("refused"),
        )

        config = OllamaConfig()
        with pytest.raises(OllamaError, match="Cannot reach Ollama"):
            generate("test", config)

    def test_timeout_error(self, mocker) -> None:
        mocker.patch(
            "chat_summarizer.ollama_client.requests.post",
            side_effect=requests.Timeout("timed out"),
        )

        config = OllamaConfig()
        with pytest.raises(OllamaError, match="timed out"):
            generate("test", config)

    def test_non_200_response(self, mocker) -> None:
        mock_resp = mocker.Mock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mocker.patch("chat_summarizer.ollama_client.requests.post", return_value=mock_resp)

        config = OllamaConfig()
        with pytest.raises(OllamaError, match="HTTP 500"):
            generate("test", config)

    def test_remote_url_rejected(self) -> None:
        """generate() must refuse to call a non-localhost URL."""
        config = OllamaConfig(base_url="https://api.example.com")
        with pytest.raises(OllamaError, match="non-localhost"):
            generate("test", config)


class TestCheckHealth:
    """Tests for health checks with mocked HTTP."""

    def test_healthy(self, mocker) -> None:
        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "models": [{"name": "qwen2.5:3b"}],
        }
        mocker.patch("chat_summarizer.ollama_client.requests.get", return_value=mock_resp)

        config = OllamaConfig()
        ok, msg = check_health(config)
        assert ok is True
        assert "ready" in msg

    def test_model_not_pulled(self, mocker) -> None:
        mock_resp = mocker.Mock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"models": [{"name": "llama3.2:3b"}]}
        mocker.patch("chat_summarizer.ollama_client.requests.get", return_value=mock_resp)

        config = OllamaConfig(model="qwen2.5:3b")
        ok, msg = check_health(config)
        assert ok is False
        assert "not pulled" in msg

    def test_ollama_not_running(self, mocker) -> None:
        mocker.patch(
            "chat_summarizer.ollama_client.requests.get",
            side_effect=requests.ConnectionError("refused"),
        )

        config = OllamaConfig()
        ok, msg = check_health(config)
        assert ok is False
        assert "Cannot reach" in msg
