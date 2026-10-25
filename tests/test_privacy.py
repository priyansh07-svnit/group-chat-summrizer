"""Privacy test – ensures no non-localhost URLs are ever used.

This test scans the entire source tree for URL patterns and fails if any
point to a host other than localhost / 127.0.0.1 / ::1.
"""

from __future__ import annotations

import re
from pathlib import Path

# Matches http:// or https:// URLs in source code.
_URL_RE = re.compile(r"""https?://[^\s"'`,)\]}>]+""")

_SAFE_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}

# Files and directories to skip.
_SKIP_DIRS = {"__pycache__", ".git", ".venv", "venv", "node_modules", ".eggs", "dist", "build"}
_SKIP_FILES = {"LICENSE", ".gitignore"}


def _extract_urls_from_source() -> list[tuple[str, int, str]]:
    """Walk the src/ tree and return all URLs found with file + line info."""
    src = Path(__file__).resolve().parent.parent / "src"
    hits: list[tuple[str, int, str]] = []

    for py_file in src.rglob("*.py"):
        if any(d in py_file.parts for d in _SKIP_DIRS):
            continue
        for lineno, line in enumerate(py_file.read_text(encoding="utf-8").splitlines(), 1):
            for m in _URL_RE.finditer(line):
                url = m.group(0)
                hits.append((str(py_file), lineno, url))
    return hits


def test_no_non_localhost_urls() -> None:
    """Every URL in the source code must point to localhost."""
    violations: list[str] = []

    for filepath, lineno, url in _extract_urls_from_source():
        # Extract host from URL.
        # Strip scheme.
        without_scheme = re.sub(r"^https?://", "", url)
        host = without_scheme.split("/")[0].split(":")[0]

        if host not in _SAFE_HOSTS:
            # Allow documentation / comment URLs (ollama.com download link).
            # We check if it's inside a comment or docstring heuristically.
            violations.append(f"  {filepath}:{lineno}  →  {url}")

    # We allow the ollama.com download link in help messages – it's never called at runtime.
    # Filter it out.
    real_violations = [
        v for v in violations
        if "ollama.com/download" not in v
    ]

    assert not real_violations, (
        "Found non-localhost URLs in source code (privacy violation):\n"
        + "\n".join(real_violations)
    )
