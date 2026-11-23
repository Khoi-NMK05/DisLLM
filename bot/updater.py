"""
GitHub Releases auto-updater for DisLLM.

Checks https://github.com/Khoi-NMK05/DisLLM/releases/latest, verifies optional
SHA-256 checksums, downloads the appropriate Windows update package, and hands
off installation so user data in %APPDATA%\\DisLLM is never touched.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import aiohttp

from bot.paths import get_exe_dir, is_frozen, is_portable_mode
from bot.version import APP_NAME, APP_VERSION, GITHUB_RELEASES_API

logger = logging.getLogger(__name__)


class UpdateError(RuntimeError):
    """Raised when checking, downloading, or applying an update fails."""


@dataclass
class ReleaseInfo:
    """Metadata for a GitHub Release."""

    version: str
    tag_name: str
    name: str
    body: str
    html_url: str
    published_at: str = ""
    installer_url: str | None = None
    installer_name: str | None = None
    portable_zip_url: str | None = None
    portable_zip_name: str | None = None
    checksums_url: str | None = None


def parse_version(version_str: str) -> tuple[int, ...]:
    """Parses a version tag like 'v1.2.3' or '1.2.3' into a comparable int tuple."""
    cleaned = version_str.strip().lstrip("vV")
    # Strip any pre-release/build suffix for numeric comparison
    core = re.split(r"[-+]", cleaned, maxsplit=1)[0]
    parts = [int(p) for p in core.split(".") if p.isdigit()]
    return tuple(parts) if parts else (0,)


def is_newer_version(latest: str, current: str = APP_VERSION) -> bool:
    """Returns True if `latest` represents a strictly higher semantic version than `current`."""
    latest_parts = list(parse_version(latest))
    current_parts = list(parse_version(current))
    max_len = max(len(latest_parts), len(current_parts))
    latest_parts.extend([0] * (max_len - len(latest_parts)))
    current_parts.extend([0] * (max_len - len(current_parts)))
    return tuple(latest_parts) > tuple(current_parts)


def detect_install_mode() -> str:
    """
    Determines how DisLLM is currently running:
      - 'source': running via Python interpreter (git checkout)
      - 'installer': installed via Inno Setup (unins000.exe present beside exe)
      - 'portable': running from a standalone extracted folder
    """
    if not is_frozen():
        return "source"
    if is_portable_mode():
        return "portable"
    if (get_exe_dir() / "unins000.exe").exists():
        return "installer"
    return "portable"


def _select_assets(assets: list[dict]) -> tuple[str | None, str | None, str | None, str | None, str | None]:
    installer_url = installer_name = None
    portable_url = portable_name = None
    checksums_url = None

    for asset in assets:
        name = str(asset.get("name", ""))
        url = asset.get("browser_download_url")
        if not name or not url:
            continue
        lower = name.lower()

        if lower == "checksums.txt" or lower.endswith("sha256sums.txt"):
            checksums_url = str(url)
        elif lower.endswith(".exe") and "setup" in lower:
            installer_url = str(url)
            installer_name = name
        elif lower.endswith(".zip") and ("win" in lower or "disllm" in lower):
            portable_url = str(url)
            portable_name = name

    return installer_url, installer_name, portable_url, portable_name, checksums_url


async def check_for_updates(
    current_version: str = APP_VERSION,
    api_url: str = GITHUB_RELEASES_API,
    timeout_seconds: float = 12.0,
) -> tuple[bool, ReleaseInfo | None]:
    """
    Queries GitHub Releases for the latest release.

    Returns:
        (has_update, release_info)
        Returns (False, None) if no releases have been published yet (HTTP 404).
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{APP_NAME}/{current_version}",
    }
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(api_url, headers=headers) as resp:
                if resp.status == 404:
                    return False, None
                if resp.status != 200:
                    raise UpdateError(f"GitHub API returned HTTP {resp.status}.")
                data = await resp.json()
    except UpdateError:
        raise
    except Exception as err:
        raise UpdateError(f"Could not reach GitHub Releases: {err}") from err

    tag_name = str(data.get("tag_name", "")).strip()
    if not tag_name:
        return False, None

    version = tag_name.lstrip("vV")
    assets = data.get("assets") or []
    inst_url, inst_name, zip_url, zip_name, sums_url = _select_assets(assets)

    info = ReleaseInfo(
        version=version,
        tag_name=tag_name,
        name=str(data.get("name") or tag_name),
        body=str(data.get("body") or "").strip(),
        html_url=str(data.get("html_url") or ""),
        published_at=str(data.get("published_at") or ""),
        installer_url=inst_url,
        installer_name=inst_name,
        portable_zip_url=zip_url,
        portable_zip_name=zip_name,
        checksums_url=sums_url,
    )
    return is_newer_version(version, current_version), info


def parse_checksums(content: str) -> dict[str, str]:
    """Parses standard `<sha256>  <filename>` lines into `{filename: sha256_lower}`."""
    result: dict[str, str] = {}
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) == 2:
            digest = parts[0].strip().lower()
            filename = parts[1].strip().lstrip("*")
            if len(digest) == 64:
                result[filename] = digest
    return result


def compute_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def verify_sha256(file_path: Path, expected_hex: str) -> bool:
    return compute_sha256(file_path) == expected_hex.strip().lower()


async def download_file(
    url: str,
    dest_path: Path,
    progress_callback: Callable[[int, int], None] | None = None,
    timeout_seconds: float = 300.0,
) -> Path:
    """Streams a file from `url` to `dest_path`, reporting `(downloaded, total)` bytes."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest_path.with_suffix(dest_path.suffix + ".part")
    headers = {"User-Agent": f"{APP_NAME}/{APP_VERSION}"}
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    raise UpdateError(f"Download failed with HTTP {resp.status}.")
                total = int(resp.headers.get("Content-Length", "0") or 0)
                downloaded = 0
                with open(tmp_path, "wb") as f:
                    async for chunk in resp.content.iter_chunked(65536):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if progress_callback:
                                progress_callback(downloaded, total)
        os.replace(tmp_path, dest_path)
        return dest_path
    except Exception as err:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        if isinstance(err, UpdateError):
            raise
        raise UpdateError(f"Download failed: {err}") from err


async def fetch_expected_checksum(checksums_url: str, asset_name: str) -> str | None:
    """Downloads checksums.txt and returns the expected SHA-256 hex for `asset_name`, if present."""
    headers = {"User-Agent": f"{APP_NAME}/{APP_VERSION}"}
    timeout = aiohttp.ClientTimeout(total=15.0)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(checksums_url, headers=headers) as resp:
                if resp.status != 200:
                    return None
                text = await resp.text()
        return parse_checksums(text).get(asset_name)
    except Exception as err:
        logger.warning("Could not fetch checksums.txt: %s", err)
        return None


def get_update_staging_dir() -> Path:
    staging = Path(tempfile.gettempdir()) / f"{APP_NAME}_update"
    staging.mkdir(parents=True, exist_ok=True)
    return staging


def launch_installer_update(installer_path: Path) -> None:
    """
    Launches the Inno Setup installer in silent upgrade mode.
    The caller should immediately exit the current application after calling this.
    """
    if not installer_path.is_file():
        raise UpdateError(f"Installer file not found: {installer_path}")

    cmd = [
        str(installer_path),
        "/SILENT",
        "/CLOSEAPPLICATIONS",
        "/RESTARTAPPLICATIONS",
    ]
    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    subprocess.Popen(cmd, creationflags=creation_flags, close_fds=True)


def launch_portable_zip_update(
    zip_path: Path,
    app_dir: Path | None = None,
    exe_name: str = f"{APP_NAME}.exe",
) -> Path:
    """
    Extracts a portable release zip into a temp folder and launches a helper
    batch script that waits for the current process to exit, replaces the
    binaries in `app_dir`, and restarts DisLLM. User data in %APPDATA%\\DisLLM
    is never modified.
    """
    if not zip_path.is_file():
        raise UpdateError(f"Update archive not found: {zip_path}")

    target_dir = (app_dir or get_exe_dir()).resolve()
    staging_root = get_update_staging_dir()
    extract_dir = staging_root / "extracted"
    if extract_dir.exists():
        shutil.rmtree(extract_dir, ignore_errors=True)
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    # If the zip contains a single top-level directory (e.g. DisLLM/), unwrap it.
    entries = list(extract_dir.iterdir())
    source_dir = entries[0] if len(entries) == 1 and entries[0].is_dir() else extract_dir

    pid = os.getpid()
    script_path = staging_root / "apply_update.bat"
    exe_path = target_dir / exe_name

    # Batch script waits for the current PID to terminate, mirrors files safely
    # (never touching %APPDATA%), relaunches DisLLM, and cleans up staging.
    batch_content = f"""@echo off
setlocal
set "PID={pid}"
set "SRC={source_dir}"
set "DST={target_dir}"
set "EXE={exe_path}"

:wait_loop
tasklist /FI "PID eq %PID%" 2>NUL | find /I "%PID%" >NUL
if "%ERRORLEVEL%"=="0" (
    timeout /t 1 /nobreak >NUL
    goto wait_loop
)

robocopy "%SRC%" "%DST%" /E /IS /IT /R:5 /W:1 >NUL
if exist "%EXE%" (
    start "" "%EXE%"
)
rmdir /S /Q "{extract_dir}" 2>NUL
del "%~f0" 2>NUL
"""
    script_path.write_text(batch_content, encoding="utf-8")

    creation_flags = 0
    if sys.platform == "win32":
        creation_flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW

    subprocess.Popen(
        ["cmd.exe", "/c", str(script_path)],
        creationflags=creation_flags,
        close_fds=True,
    )
    return script_path
