# Copyright 2026 EagleEye Guardian Contributors
# SPDX-License-Identifier: Apache-2.0

"""Public repository & security hygiene gate (Requirement 0)."""

from __future__ import annotations

import pathlib
import re
import subprocess

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
}

SKIP_SUFFIXES = {".pyc", ".png", ".jpg", ".jpeg", ".ico", ".woff", ".woff2", ".lock"}

# Patterns that must never appear in a public repository
FORBIDDEN_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Google API Key", re.compile(r"AIza[0-9A-Za-z\-_]{35}")),
    ("Private Key Header", re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----")),
    ("Internal Shortlink", re.compile(r"\b(?:http://|https://)?(?:go|b|cl|oma)/[a-zA-Z0-9_\-]{3,}")),
    ("Internal Corp Domain", re.compile(r"\b[a-zA-Z0-9._%+-]+@google\.com\b")),
    ("Internal Corp Host", re.compile(r"https?://[a-zA-Z0-9.\-]*\.corp\.google\.com\b")),
]


def _iter_repo_files() -> list[pathlib.Path]:
    """Return tracked files (or all non-ignored files if git index is not yet populated)."""
    try:
        proc = subprocess.run(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            tracked = [
                REPO_ROOT / line.strip()
                for line in proc.stdout.splitlines()
                if line.strip() and (REPO_ROOT / line.strip()).is_file()
            ]
            if tracked:
                return tracked
    except OSError:
        pass

    files: list[pathlib.Path] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix in SKIP_SUFFIXES or path.name == "package-lock.json" or path.name == "uv.lock":
            continue
        files.append(path)
    return files


def test_no_secrets_internal_urls_or_customer_ids() -> None:
    """Scan all repository files to ensure zero secrets, internal shortlinks, or corp emails exist."""
    files = _iter_repo_files()
    assert len(files) >= 10, "Expected repository files to be scanned."

    violations: list[str] = []
    for file_path in files:
        if file_path.name in ("package-lock.json", "uv.lock"):
            continue
        try:
            content = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        rel = file_path.relative_to(REPO_ROOT)
        for label, pattern in FORBIDDEN_PATTERNS:
            match = pattern.search(content)
            if match:
                violations.append(f"{rel}: matched {label} ({match.group(0)!r})")

    assert not violations, "Public repo hygiene violations found:\n" + "\n".join(violations)


def test_env_example_uses_clean_placeholders() -> None:
    """Verify .env.example uses 'your-gcp-project-id' and required model environment variables."""
    env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "GOOGLE_CLOUD_PROJECT=your-gcp-project-id" in env_example
    assert "GOOGLE_CLOUD_LOCATION=" in env_example
    assert "SRE_ROUTER_MODEL=gemini-2.5-flash" in env_example
    assert "SRE_SPECIALIST_MODEL=gemini-2.5-pro" in env_example
    assert "A2UI_IFRAME_BASE_URL=" in env_example


def test_apache_2_license_and_headers_present() -> None:
    """Verify root LICENSE is Apache 2.0 and Python/TS source files carry SPDX Apache-2.0 headers."""
    license_file = REPO_ROOT / "LICENSE"
    assert license_file.is_file()
    license_text = license_file.read_text(encoding="utf-8")
    assert "Apache License" in license_text
    assert "Version 2.0, January 2004" in license_text

    source_files = list((REPO_ROOT / "eagleeye-sre-agent" / "app").rglob("*.py")) + list(
        (REPO_ROOT / "a2ui-iframe" / "src").rglob("*.ts*")
    )
    assert source_files, "Expected source files in app/ and a2ui-iframe/src/"
    for src in source_files:
        head = src.read_text(encoding="utf-8")[:300]
        assert "Apache-2.0" in head, f"Missing SPDX Apache-2.0 header in {src}"
