#!/usr/bin/env bash
# =============================================================================
# One-shot build wrapper.
# =============================================================================
#   scripts/build.sh                 # validate layout + compile
#   scripts/build.sh config          # validate layout + dump the merged config
#   scripts/build.sh run             # compile + flash + logs
#   scripts/build.sh upload          # compile + OTA upload
#
# Environment overrides:
#   CONFIG        entry-point YAML            (default e1003-dashboard.yaml)
#   FONT_REGULAR  regular TTF path
#   FONT_BOLD     bold TTF path
#   SKIP_LAYOUT   set to 1 to skip the layout regeneration step
#
# Anything after the subcommand is forwarded to esphome verbatim, so `-s key
# value` build flags still work:
#   scripts/build.sh compile -s ha_light_entity light.other
# =============================================================================
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

CONFIG="${CONFIG:-e1003-dashboard.yaml}"
COMMAND="${1:-compile}"
shift || true

# uv owns the toolchain (see pyproject.toml). No global esphome install needed.
if ! command -v uv >/dev/null; then
  echo "uv is required: https://docs.astral.sh/uv/" >&2
  exit 1
fi

# Regenerate layout/generated/* from layout/ui_layout.yaml unless asked not to.
if [[ "${SKIP_LAYOUT:-0}" != "1" ]]; then
  uv run python tools/layout_to_h.py
fi

# Pick fonts that exist on this machine. Arial and Liberation Sans are
# metric-compatible, so the layout is identical either way.
FONT_ARGS=()
if [[ -n "${FONT_REGULAR:-}" && -n "${FONT_BOLD:-}" ]]; then
  FONT_ARGS=(-s font_regular "$FONT_REGULAR" -s font_bold "$FONT_BOLD")
elif [[ -f /usr/share/fonts/liberation/LiberationSans-Regular.ttf ]]; then
  FONT_ARGS=(-s font_regular /usr/share/fonts/liberation/LiberationSans-Regular.ttf
             -s font_bold /usr/share/fonts/liberation/LiberationSans-Bold.ttf)
elif [[ -f /Library/Fonts/Arial.ttf ]]; then
  FONT_ARGS=(-s font_regular /Library/Fonts/Arial.ttf -s font_bold "/Library/Fonts/Arial Bold.ttf")
fi

exec uv run esphome ${FONT_ARGS[@]+"${FONT_ARGS[@]}"} "$COMMAND" "$CONFIG" "$@"