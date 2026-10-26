#!/usr/bin/env bash
# Compatibility wrapper. scripts/build.py is the cross-platform build driver.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
exec uv run python scripts/build.py "$@"
