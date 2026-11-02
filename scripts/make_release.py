#!/usr/bin/env python3
"""Assemble release artifacts from a finished ESPHome build.

Turns `.esphome/build/<device>/build/` into the layout the release workflow
publishes and that a CDN can mirror unchanged:

    dist/                     release assets
      firmware.factory.bin    merged image, flashed at offset 0
      firmware.ota.bin        OTA image
      manifest.json           ESP Web Tools manifest
      firmware.json           machine-readable release index
      SHA256SUMS

    dist-pages/               browser installer (with --pages-out)
      index.html
      manifest.json
      firmware.factory.bin

File names are deliberately stable and unversioned so that
`releases/latest/download/firmware.ota.bin` keeps working; the version lives in
the tag, in manifest.json and in firmware.json.

Usage:
    uv run python scripts/make_release.py --version 1.2.3 --pages-out dist-pages
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import layout_to_h  # noqa: E402  (needs the sys.path entry above)

# Placeholders the installer page is built from, spelled @@NAME@@ on purpose:
# {{...}} is what ESPHome uses for substitutions and is also a plausible
# password value, so it would collide.
TOKEN = re.compile(r"@@([A-Z_]+)@@")


def fill_installer(template: str, values: dict[str, str]) -> str:
    """Substitute @@TOKEN@@ placeholders, refusing to ship a half-filled page.

    Checks both directions: a token left unfilled in the output, and a value
    the template never asked for -- the latter silently ships a stale
    hardcoded default, which is how the repo URL nearly went out wrong.
    """
    missing = sorted(key for key in values if f"@@{key}@@" not in template)
    if missing:
        raise Problem(f"installer template has no placeholder for: {', '.join(missing)}")
    filled = TOKEN.sub(lambda match: values.get(match.group(1), match.group(0)), template)
    leftover = sorted(set(TOKEN.findall(filled)))
    if leftover:
        raise Problem(f"installer template has unfilled placeholders: {', '.join(leftover)}")
    return filled

# ESP-IDF names the target lowercase in flasher_args.json; esp-web-tools
# accepts only these spellings.
CHIP_FAMILIES = {
    "esp32": "ESP32",
    "esp32s2": "ESP32-S2",
    "esp32s3": "ESP32-S3",
    "esp32c2": "ESP32-C2",
    "esp32c3": "ESP32-C3",
    "esp32c5": "ESP32-C5",
    "esp32c6": "ESP32-C6",
    "esp32c61": "ESP32-C61",
    "esp32h2": "ESP32-H2",
    "esp32p4": "ESP32-P4",
}

# Every ESP32 image starts with this byte.
IMAGE_MAGIC = 0xE9

FACTORY = "firmware.factory.bin"
OTA = "firmware.ota.bin"


class Problem(Exception):
    pass


def default_build_dir() -> Path:
    """The build directory belonging to the device the config names.

    Falls back to a scan, but never guesses between several builds: a stale
    build tree from a different configuration must not end up in a release.
    """
    device = layout_to_h.entry_substitutions().get("device_name")
    if device:
        candidate = ROOT / ".esphome" / "build" / str(device) / "build"
        if (candidate / FACTORY).is_file():
            return candidate

    found = sorted(p.parent for p in (ROOT / ".esphome" / "build").glob("*/build/" + FACTORY))
    if not found:
        raise Problem(
            "no built firmware found under .esphome/build/. "
            "Run `uv run python scripts/build.py compile` first."
        )
    names = ", ".join(p.parent.name for p in found)
    raise Problem(
        f"no build for device_name '{device}' (found: {names}); "
        "pass --build-dir explicitly"
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_chip(build_dir: Path) -> str:
    """chipFamily for the manifest, taken from the build, never hardcoded."""
    args_file = build_dir / "flasher_args.json"
    if not args_file.is_file():
        raise Problem(f"{args_file} is missing; cannot determine the chip")
    chip = json.loads(args_file.read_text()).get("extra_esptool_args", {}).get("chip", "")
    if chip not in CHIP_FAMILIES:
        raise Problem(f"unknown chip '{chip}' in {args_file.name}")
    return CHIP_FAMILIES[chip]


def check_image(path: Path) -> None:
    """Refuse to publish something that is not an ESP32 image."""
    if not path.is_file() or path.stat().st_size == 0:
        raise Problem(f"{path.name} is missing or empty")
    if path.open("rb").read(1)[0] != IMAGE_MAGIC:
        raise Problem(f"{path.name} does not start with 0x{IMAGE_MAGIC:02X}; refusing to publish")


def make_manifest(name: str, version: str, chip: str) -> dict:
    return {
        "name": name,
        "version": version,
        "home_assistant_domain": "esphome",
        "new_install_prompt_erase": True,
        "new_install_improv_wait_time": 30,
        "builds": [
            {
                "chipFamily": chip,
                "parts": [{"path": FACTORY, "offset": 0}],
            }
        ],
    }


def make_index(meta: dict, files: list[Path]) -> dict:
    return {
        **meta,
        "files": [
            {
                "name": path.name,
                "size": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files
        ],
    }


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def git(*args: str, fallback: str) -> str:
    try:
        return subprocess.check_output(
            ("git", *args), cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return fallback


def esphome_version() -> str:
    try:
        from importlib.metadata import version

        return version("esphome")
    except Exception:  # pragma: no cover - only when run outside the uv env
        return "unknown"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=ROOT / "e1003-dashboard.yaml",
        help="firmware entry point used for substitutions and build selection",
    )
    parser.add_argument("--build-dir", type=Path, help="default: auto-detect under .esphome/build")
    parser.add_argument("--version", default=git("describe", "--tags", "--always", fallback="0.0.0"))
    parser.add_argument("--commit", default=git("rev-parse", "--short", "HEAD", fallback="unknown"))
    parser.add_argument("--out", type=Path, default=ROOT / "dist")
    parser.add_argument("--pages-out", type=Path, help="also emit the browser installer here")
    parser.add_argument(
        "--installer", type=Path, default=ROOT / "web" / "install.html",
        help="template copied to the installer page",
    )
    parser.add_argument("--repo-url", default=None, help="default: the origin remote")
    args = parser.parse_args(argv)

    try:
        if not args.config.is_file():
            raise Problem(f"{args.config} is missing")
        os.environ["CONFIG"] = str(args.config.resolve())

        build_dir = args.build_dir or default_build_dir()
        factory, ota = build_dir / FACTORY, build_dir / OTA
        check_image(factory)
        check_image(ota)
        chip = read_chip(build_dir)
        substitutions = layout_to_h.entry_substitutions()
        device = substitutions.get("device_name", "esp32")
        name = substitutions.get("friendly_name", device)

        version = args.version.lstrip("v")
        meta = {
            "name": name,
            "device": device,
            "version": version,
            "tag": args.version if args.version.startswith("v") else f"v{version}",
            "commit": args.commit,
            "esphome": esphome_version(),
            "chip": chip,
            "built": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        }

        out = args.out.resolve()
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True)

        manifest = make_manifest(name, version, chip)
        copied = []
        for source in (factory, ota):
            target = out / source.name
            shutil.copy2(source, target)
            copied.append(target)
        write_json(out / "manifest.json", manifest)
        copied.append(out / "manifest.json")

        write_json(out / "firmware.json", make_index(meta, copied))
        checksums = out / "SHA256SUMS"
        checksums.write_text("".join(f"{sha256(p)}  {p.name}\n" for p in sorted(copied)))

        for path in sorted(out.iterdir()):
            print(f"  {path.stat().st_size:>9,}  {path.relative_to(out.parent)}")

        if args.pages_out:
            pages = args.pages_out.resolve()
            if pages.exists():
                shutil.rmtree(pages)
            pages.mkdir(parents=True)

            values = {
                "REPO_URL": args.repo_url
                or git("remote", "get-url", "origin", fallback="").removesuffix(".git"),
            }
            empty = sorted(key for key, value in values.items() if not value)
            if empty:
                raise Problem(f"installer value(s) came out empty: {', '.join(empty)}")

            (pages / "index.html").write_text(
                fill_installer(args.installer.read_text(), values)
            )
            shutil.copy2(factory, pages / FACTORY)
            write_json(pages / "manifest.json", manifest)
            for path in sorted(pages.iterdir()):
                print(f"  {path.stat().st_size:>9,}  {path.relative_to(pages.parent)}")

    except Problem as problem:
        print(f"error: {problem}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
