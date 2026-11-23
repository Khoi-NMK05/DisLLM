"""
Application version and repository metadata for DisLLM.
Single source of truth used by the GUI, auto-updater, build script, and installer.
"""

from __future__ import annotations

APP_NAME = "DisLLM"
APP_VERSION = "1.0.0"

GITHUB_OWNER = "Khoi-NMK05"
GITHUB_REPO = "DisLLM"
GITHUB_REPO_SLUG = f"{GITHUB_OWNER}/{GITHUB_REPO}"
GITHUB_REPO_URL = f"https://github.com/{GITHUB_REPO_SLUG}"
GITHUB_RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO_SLUG}/releases/latest"
GITHUB_RELEASES_URL = f"{GITHUB_REPO_URL}/releases"
