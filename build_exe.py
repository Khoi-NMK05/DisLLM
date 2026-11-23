"""
Automated Windows Build & Release Packaging Script for DisLLM.

Builds:
  1. PyInstaller --onedir bundle: dist/DisLLM/DisLLM.exe
  2. Portable Windows zip:       dist/DisLLM-v<VERSION>-win64.zip
  3. Windows Inno Setup installer (if Inno Setup 6 ISCC.exe is installed):
                                 dist/DisLLM-Setup-v<VERSION>.exe
  4. SHA-256 checksums file:     dist/checksums.txt

User data (.env, SQLite DB, AI personas, custom commands, plugins) lives in
%APPDATA%\\DisLLM at runtime, so rebuilding or upgrading never wipes user saves.

Usage:
  python build_exe.py
  python build_exe.py --skip-installer
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from bot.version import APP_NAME, APP_VERSION

ROOT_DIR = Path(__file__).resolve().parent
DIST_DIR = ROOT_DIR / "dist"
BUNDLE_DIR = DIST_DIR / APP_NAME
ISS_SCRIPT = ROOT_DIR / "installer" / "DisLLM.iss"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().lower()


def _find_iscc() -> Path | None:
    """Locates Inno Setup 6 compiler (ISCC.exe) if installed."""
    on_path = shutil.which("ISCC") or shutil.which("iscc")
    if on_path:
        return Path(on_path)
    candidates = [
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Inno Setup 6" / "ISCC.exe",
        Path.home() / "AppData" / "Local" / "Programs" / "Inno Setup 6" / "ISCC.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _create_portable_zip(bundle_dir: Path, zip_path: Path) -> Path:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for file_path in sorted(bundle_dir.rglob("*")):
            if file_path.is_file():
                arcname = Path(APP_NAME) / file_path.relative_to(bundle_dir)
                zf.write(file_path, arcname)
    return zip_path


def _write_checksums(artifacts: list[Path], out_path: Path) -> None:
    lines = [f"{_sha256(p)}  {p.name}" for p in artifacts if p.is_file()]
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build(skip_installer: bool = False) -> None:
    print("=" * 64)
    print(f" Building {APP_NAME} v{APP_VERSION} for Windows ")
    print("=" * 64)

    # Terminate any previously running instance so files are not locked
    if sys.platform == "win32":
        for proc in (f"{APP_NAME}.exe", "DiscordAICompanion.exe"):
            subprocess.run(["taskkill", "/F", "/IM", proc], capture_output=True)

    pyinstaller_cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        f"--name={APP_NAME}",
        "--onedir",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--collect-all=bot",
        "--hidden-import=bot",
        "--hidden-import=bot.cogs",
        "--hidden-import=bot.cogs.chat",
        "--hidden-import=bot.cogs.commands",
        "--hidden-import=aiohttp",
        "--hidden-import=aiosqlite",
        "--hidden-import=discord",
        "--hidden-import=discord.ext.commands",
        "--hidden-import=ollama",
        "--hidden-import=PySide6",
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtGui",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=qasync",
        "--hidden-import=ddgs",
        "app.py",
    ]

    print("\nRunning PyInstaller:")
    print(" ".join(pyinstaller_cmd))
    print("-" * 64)

    result = subprocess.run(pyinstaller_cmd, cwd=ROOT_DIR)
    if result.returncode != 0:
        print(f"\nBUILD FAILED with exit code: {result.returncode}")
        sys.exit(result.returncode)

    if not BUNDLE_DIR.is_dir():
        print(f"\nExpected bundle directory not found: {BUNDLE_DIR}")
        sys.exit(1)

    artifacts: list[Path] = []

    # 1. Portable zip archive
    zip_path = DIST_DIR / f"{APP_NAME}-v{APP_VERSION}-win64.zip"
    print(f"\nCreating portable archive: {zip_path.name}")
    _create_portable_zip(BUNDLE_DIR, zip_path)
    artifacts.append(zip_path)

    # 2. Inno Setup installer (optional locally; always built in GitHub Actions)
    installer_path = DIST_DIR / f"{APP_NAME}-Setup-v{APP_VERSION}.exe"
    if not skip_installer and sys.platform == "win32" and ISS_SCRIPT.is_file():
        iscc = _find_iscc()
        if iscc:
            print(f"\nBuilding Windows installer with Inno Setup ({iscc})...")
            iscc_cmd = [
                str(iscc),
                f"/DAppVersion={APP_VERSION}",
                f"/DAppName={APP_NAME}",
                f"/DSourceDir={BUNDLE_DIR}",
                f"/DOutputDir={DIST_DIR}",
                str(ISS_SCRIPT),
            ]
            iscc_result = subprocess.run(iscc_cmd, cwd=ROOT_DIR)
            if iscc_result.returncode != 0:
                print(f"Inno Setup failed with exit code: {iscc_result.returncode}")
                sys.exit(iscc_result.returncode)
            if installer_path.is_file():
                artifacts.append(installer_path)
        else:
            print(
                "\n[Info] Inno Setup 6 (ISCC.exe) not found locally — skipped Setup.exe.\n"
                "       Install Inno Setup 6 locally OR push a git tag (vX.Y.Z) to let\n"
                "       GitHub Actions build DisLLM-Setup-vX.Y.Z.exe automatically."
            )

    # 3. SHA-256 checksums for the auto-updater
    checksums_path = DIST_DIR / "checksums.txt"
    _write_checksums(artifacts, checksums_path)

    print("\n" + "=" * 64)
    print(f" BUILD SUCCESSFUL — {APP_NAME} v{APP_VERSION}")
    print(f" Executable: {BUNDLE_DIR / f'{APP_NAME}.exe'}")
    for art in artifacts:
        print(f" Release asset: {art}")
    print(f" Checksums: {checksums_path}")
    print(" User data is stored safely in %APPDATA%\\DisLLM (never wiped on rebuild).")
    print("=" * 64)


def main() -> None:
    parser = argparse.ArgumentParser(description=f"Build {APP_NAME} Windows release artifacts.")
    parser.add_argument(
        "--skip-installer",
        action="store_true",
        help="Skip Inno Setup installer creation even if ISCC.exe is installed.",
    )
    args = parser.parse_args()
    build(skip_installer=args.skip_installer)


if __name__ == "__main__":
    main()
