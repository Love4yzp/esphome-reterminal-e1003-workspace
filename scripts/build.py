#!/usr/bin/env python3
"""Cross-platform build driver.

One entry point for Linux, Windows and macOS -- there is no `build.sh` /
`build.bat` pair to keep in sync, and no host font to detect.

    uv run python scripts/build.py                 # layout check + compile
    uv run python scripts/build.py config          # layout check + merged config
    uv run python scripts/build.py run             # compile + flash + logs
    uv run python scripts/build.py upload          # compile + OTA upload
    uv run python scripts/build.py logs            # serial/OTA logs
    uv run python scripts/build.py compile -s default_light_target light.other

Anything after the subcommand is forwarded to esphome verbatim, so `-s key
value` build flags still work.

Environment overrides:
    CONFIG        entry-point YAML           (default e1003-dashboard.yaml)
    SKIP_LAYOUT   set to 1 to skip the layout regeneration step
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LAYOUT_TOOL = REPO / "tools" / "layout_to_h.py"
DEFAULT_CONFIG = "e1003-dashboard.yaml"

# Git-Bash and MSys export these; the ESP-IDF toolchain then resolves MinGW
# flavoured paths and the build fails deep inside cmake. Blank them.
MSYS_VARS = frozenset(
    {
        "MSYSTEM",
        "MSYSTEM_CARCH",
        "MSYSTEM_CHOST",
        "MSYSTEM_PREFIX",
        "MSYS",
        "MSYS2_PATH_TYPE",
        "MINGW_PREFIX",
        "MINGW_CHOST",
        "MINGW_PACKAGE_PREFIX",
        "EXEPATH",
        "OSTYPE",
        "SHELL",
        "TERM",
        "SHLVL",
        "OLDPWD",
        "BASH_ENV",
    }
)

# PATH entries owned by an MSys installation. They are dropped one by one
# rather than resetting PATH wholesale: a wholesale reset would hide the
# interpreter and `uv` themselves.
MSYS_PATH_MARKERS = (
    "\\msys64\\",
    "\\msys32\\",
    "\\git\\usr\\bin",
    "\\git\\mingw",
    "\\mingw32\\",
    "\\mingw64\\",
    "\\usr\\bin",
)


def clean_windows_env(env: dict[str, str]) -> dict[str, str]:
    """Strip Git-Bash/MSys leakage from a child environment.

    Windows-only in practice, but kept free of platform APIs so it can be
    exercised on any host.
    """
    cleaned = {key: value for key, value in env.items() if key not in MSYS_VARS}

    if userprofile := cleaned.get("USERPROFILE"):
        cleaned["HOME"] = userprofile

    if path := cleaned.get("PATH"):
        # A Windows PATH always uses ';', whatever host this runs on.
        kept = [entry for entry in path.split(";") if not _is_msys_path(entry)]
        cleaned["PATH"] = ";".join(kept)

    return cleaned


def _is_msys_path(entry: str) -> bool:
    lowered = entry.lower()
    return any(marker in lowered for marker in MSYS_PATH_MARKERS)


def main(argv: list[str]) -> int:
    if importlib.util.find_spec("esphome") is None:
        print(
            "esphome is not importable from this interpreter.\n"
            "Run the driver through uv so the pinned toolchain in uv.lock is used:\n"
            "  uv run python scripts/build.py",
            file=sys.stderr,
        )
        return 1

    # A leading flag means the caller omitted the subcommand: `build.py -s x y`
    # is a compile with extra flags, not a subcommand called "-s".
    if argv and not argv[0].startswith("-"):
        command, extra = argv[0], list(argv[1:])
    else:
        command, extra = "compile", list(argv)

    config = os.environ.get("CONFIG", DEFAULT_CONFIG)
    env = clean_windows_env(dict(os.environ)) if os.name == "nt" else None

    if os.environ.get("SKIP_LAYOUT") != "1":
        print("[build] regenerating layout/generated/ from layout/ui_layout.yaml")
        code = subprocess.call([sys.executable, str(LAYOUT_TOOL)], cwd=REPO, env=env)
        if code != 0:
            return code

    forwarded = " ".join(extra)
    print(f"[build] esphome {command} {config}{f' {forwarded}' if forwarded else ''}")
    return subprocess.call(
        [sys.executable, "-m", "esphome", command, config, *extra],
        cwd=REPO,
        env=env,
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
