#!/usr/bin/env python3
"""E1003 layout compiler.

Turns `layout/ui_layout.yaml` (the single source of truth for every screen
coordinate, font choice and touch hit box) into the artifacts the firmware and
the ESPHome config actually consume:

    layout/generated/ui_layout.h    C++ geometry + touch zone table
    layout/generated/fonts.yaml     ESPHome `font:` block
    layout/generated/policy.yaml    ESPHome `substitutions:` block (refresh policy)

Usage:
    python tools/layout_to_h.py            # validate + regenerate
    python tools/layout_to_h.py --check    # validate only (exit 1 on problems)
    python tools/layout_to_h.py --print    # print a human/HA mapping table
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is required:  uv run --with pyyaml python tools/layout_to_h.py")

REPO = Path(__file__).resolve().parent.parent
LAYOUT_FILE = REPO / "layout" / "ui_layout.yaml"
GEN_DIR = REPO / "layout" / "generated"
HEADER_OUT = GEN_DIR / "ui_layout.h"
FONTS_OUT = GEN_DIR / "fonts.yaml"
POLICY_OUT = GEN_DIR / "policy.yaml"
PACKAGES_DIR = REPO / "packages"

ALIGN_MAP = {
    "top_left": "TOP_LEFT",
    "top_center": "TOP_CENTER",
    "top_right": "TOP_RIGHT",
    "center_left": "CENTER_LEFT",
    "center": "CENTER",
    "center_right": "CENTER_RIGHT",
    "baseline_left": "BASELINE_LEFT",
    "baseline_center": "BASELINE_CENTER",
    "baseline_right": "BASELINE_RIGHT",
}

OP_MAP = {"toggle": "TOGGLE", "call": "CALL", "script": "SCRIPT"}

SOURCE_MAP = {
    "clock": "CLOCK",
    "rtc": "RTC",
    "sensor": "SENSOR",
    "text": "TEXT",
    "light_state": "LIGHT_STATE",
    "light_value": "LIGHT_VALUE",
}


class Problems(list):
    def add(self, where: str, message: str) -> None:
        self.append(f"{where}: {message}")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def short_name(name: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "_", name.upper()).strip("_")


def c_string(value: str | None) -> str:
    if value is None:
        return "nullptr"
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def rect(entry: dict, where: str, problems: Problems) -> tuple[int, int, int, int]:
    missing = {"x", "y", "w", "h"} - set(entry)
    if missing:
        problems.add(where, f"missing keys {sorted(missing)}")
        return (0, 0, 0, 0)
    values = (entry["x"], entry["y"], entry["w"], entry["h"])
    if any(not isinstance(v, int) for v in values):
        problems.add(where, "x/y/w/h must be integers")
    if values[2] <= 0 or values[3] <= 0:
        problems.add(where, "w/h must be positive")
    return values


def area(entry: dict, where: str, problems: Problems) -> tuple[int, int, int, int]:
    missing = {"x1", "y1", "x2", "y2"} - set(entry)
    if missing:
        problems.add(where, f"missing keys {sorted(missing)}")
        return (0, 0, 0, 0)
    values = (entry["x1"], entry["y1"], entry["x2"], entry["y2"])
    if values[0] >= values[2] or values[1] >= values[3]:
        problems.add(where, "x1<x2 and y1<y2 required")
    return values


def point(entry: dict, where: str, problems: Problems) -> tuple[int, int]:
    missing = {"x", "y"} - set(entry)
    if missing:
        problems.add(where, f"missing keys {sorted(missing)}")
        return (0, 0)
    return (entry["x"], entry["y"])


def declared_ids() -> set[str]:
    """Every `id: <name>` declared anywhere under packages/.

    Catches both list styles ESPHome accepts:
        - id: foo
        - platform: bar\n    id: foo
    """
    found: set[str] = set()
    for path in PACKAGES_DIR.glob("*.yaml"):
        text = path.read_text()
        for match in re.finditer(r"^-\s*id:\s*([A-Za-z_][A-Za-z0-9_]*)", text, re.M):
            found.add(match.group(1))
        for match in re.finditer(r"^\s+id:\s*([A-Za-z_][A-Za-z0-9_]*)", text, re.M):
            found.add(match.group(1))
    return found


# ---------------------------------------------------------------------------
# validation
# ---------------------------------------------------------------------------
def validate(cfg: dict) -> Problems:
    problems = Problems()

    canvas = cfg.get("meta", {}).get("canvas", {})
    cw, ch = canvas.get("width", 0), canvas.get("height", 0)
    if cw <= 0 or ch <= 0:
        problems.add("meta.canvas", "width/height must be positive")
        return problems

    fonts = {f["id"] for f in cfg.get("fonts", [])}
    if not fonts:
        problems.add("fonts", "at least one font is required")

    ids = declared_ids()

    controls = {}
    runtime = cfg.get("runtime", {})
    for control in runtime.get("controls", []):
        for key, value in control.items():
            if key == "id":
                continue
            if value not in ids:
                problems.add(
                    f"runtime.controls[{control.get('id')}].{key}",
                    f"'{value}' is not declared as a text id under packages/",
                )
        controls[control["id"]] = control

    for key in ("text",):
        if (value := runtime.get("message", {}).get(key)) and value not in ids:
            problems.add("runtime.message", f"'{value}' is not declared under packages/")

    # ---- zones -----------------------------------------------------------
    seen_zones: set[str] = set()
    for zone in cfg.get("zones", []):
        zid = zone.get("id", "?")
        where = f"zones[{zid}]"
        if zid in seen_zones:
            problems.add(where, "duplicate zone id")
        seen_zones.add(zid)

        x1, y1, x2, y2 = area(zone.get("area", {}), where, problems)
        if not (0 <= x1 < cw and 0 <= x2 < cw and 0 <= y1 < ch and 0 <= y2 < ch):
            problems.add(where, "hit box outside the canvas")

        control = zone.get("control")
        if control and control not in controls:
            problems.add(where, f"unknown control '{control}'")
        if zone.get("op") not in OP_MAP:
            problems.add(where, f"unknown op '{zone.get('op')}'")
        if zone.get("op") == "script" and control:
            problems.add(where, "'script' op does not take a control")

    # ---- cards -----------------------------------------------------------
    seen_fields: set[str] = set()
    used_fonts: set[str] = set()
    for card_name, card in cfg.get("cards", {}).items():
        if (control := card.get("control")) and control not in controls:
            problems.add(f"cards.{card_name}", f"unknown control '{control}'")

        if clear := card.get("clear"):
            x, y, w, h = rect(clear, f"cards.{card_name}.clear", problems)
            if x + w > cw or y + h > ch:
                problems.add(f"cards.{card_name}.clear", "extends past the canvas")

        for field in card.get("fields", []):
            fid = field.get("id", "?")
            where = f"cards.{card_name}.fields[{fid}]"
            if fid in seen_fields:
                problems.add(where, "duplicate field id")
            seen_fields.add(fid)

            # A "gauge" field (a bar) has geometry only: no text, no anchor.
            gauge = bool(field.get("track"))

            if (font := field.get("font")) is None:
                if not gauge:
                    problems.add(where, "text fields need a font")
            elif font not in fonts:
                problems.add(where, f"font '{font}' is not declared in fonts:")
            if font:
                used_fonts.add(font)

            if (align := field.get("align")) is None:
                if not gauge:
                    problems.add(where, "text fields need an align")
            elif align not in ALIGN_MAP:
                problems.add(where, f"unknown align '{align}'")
            if field.get("source") not in SOURCE_MAP:
                problems.add(where, f"unknown source '{field.get('source')}'")

            source = field.get("source")
            if source == "sensor" and field.get("sensor") not in ids:
                problems.add(where, f"sensor '{field.get('sensor')}' is not declared under packages/")
            if source == "sensor" and not field.get("format"):
                problems.add(where, "'sensor' fields need a printf format")
            if field.get("fallback") == "greeting" and source != "text":
                problems.add(where, "'fallback: greeting' only applies to text fields")

            for key in ("clear", "fill", "track"):
                if entry := field.get(key):
                    x, y, w, h = rect(entry, f"{where}.{key}", problems)
                    if x + w > cw or y + h > ch:
                        problems.add(f"{where}.{key}", "extends past the canvas")
            if anchor := field.get("anchor"):
                x, y = point(anchor, f"{where}.anchor", problems)
                if not (0 <= x <= cw and 0 <= y <= ch):
                    problems.add(f"{where}.anchor", "anchor outside the canvas")
            elif not gauge:
                problems.add(where, "anchor is required")

    for font in sorted(fonts - used_fonts):
        problems.add("fonts", f"'{font}' is declared but never used (wastes flash)")

    return problems


# ---------------------------------------------------------------------------
# code generation
# ---------------------------------------------------------------------------
def emit_header(cfg: dict) -> str:
    canvas = cfg["meta"]["canvas"]
    bitmap = cfg["bitmap"]
    palette = cfg.get("palette", {})
    runtime = cfg.get("runtime", {})
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    out: list[str] = []
    add = out.append

    add("#pragma once")
    add("")
    add("// ============================================================")
    add("// AUTO GENERATED FILE -- DO NOT EDIT")
    add("//")
    add("// source : layout/ui_layout.yaml")
    add("// tool   : tools/layout_to_h.py")
    add(f"// built  : {stamp}")
    add("// ============================================================")
    add("")
    add("#include <cstdint>")
    add("#include <cstddef>")
    add("")
    add("namespace e1003 {")
    add("")
    add("struct Rect { uint16_t x; uint16_t y; uint16_t w; uint16_t h; };")
    add("struct Area { uint16_t x1; uint16_t y1; uint16_t x2; uint16_t y2; };")
    add("struct Point { uint16_t x; uint16_t y; };")
    add("")
    add(f"static constexpr uint16_t CANVAS_WIDTH = {canvas['width']};")
    add(f"static constexpr uint16_t CANVAS_HEIGHT = {canvas['height']};")
    add("")
    add("// ---- static bitmap -------------------------------------------")
    add(f"static constexpr uint16_t BITMAP_WIDTH = {bitmap['width']};")
    add(f"static constexpr uint16_t BITMAP_HEIGHT = {bitmap['height']};")
    add("")
    add("// ---- grayscale palette ---------------------------------------")
    for name, value in palette.items():
        add(f"static constexpr uint8_t {short_name(name)} = {value};")
    add("")
    add("// ---- refresh policy ------------------------------------------")
    add("// (the timing values live in layout/generated/policy.yaml and are")
    add("//  consumed by the YAML side, these are the GUI-safe constants)")
    add("")
    add("// ---- field source kinds --------------------------------------")
    for index, name in enumerate(SOURCE_MAP.values()):
        add(f"static constexpr uint8_t SOURCE_{name} = {index};")
    add("")
    add("// ---- runtime control ids -------------------------------------")
    add("enum class ZoneOp : uint8_t { TOGGLE, CALL, SCRIPT };")
    add("")
    add("struct Control { const char *id; };")
    add("static constexpr Control CONTROLS[] = {")
    for control in runtime.get("controls", []):
        add(f"  {{{c_string(control['id'])}}},")
    add("};")
    add(f"static constexpr size_t CONTROL_COUNT = {len(runtime.get('controls', []))};")
    add("")
    add("// ---- touch zones ---------------------------------------------")
    add("struct Zone {")
    add("  const char *id;")
    add("  Area area;")
    add("  const char *control;")
    add("  ZoneOp op;")
    add("  const char *data_key;")
    add("  const char *data_value;")
    add("};")
    add("")
    add("static constexpr Zone ZONES[] = {")
    for zone in cfg.get("zones", []):
        x1, y1, x2, y2 = (zone["area"][k] for k in ("x1", "y1", "x2", "y2"))
        data = zone.get("data") or {}
        key = next(iter(data), None)
        value = data[key] if key else None
        add(
            f"  {{{c_string(zone['id'])}, {{{x1}, {y1}, {x2}, {y2}}}, "
            f"{c_string(zone.get('control'))}, ZoneOp::{OP_MAP[zone['op']]}, "
            f"{c_string(key)}, {c_string(str(value) if value is not None else None)}}},"
        )
    add("};")
    add(f"static constexpr size_t ZONE_COUNT = {len(cfg.get('zones', []))};")
    add("")

    for card_name, card in cfg.get("cards", {}).items():
        add(f"// ---- card: {card_name} " + "-" * max(0, 44 - len(card_name)))
        if clear := card.get("clear"):
            x, y, w, h = (clear[k] for k in ("x", "y", "w", "h"))
            add(f"static constexpr Rect {short_name(card_name)}_CLEAR{{{x}, {y}, {w}, {h}}};")
        for field in card.get("fields", []):
            fid = short_name(field["id"])
            src = SOURCE_MAP[field["source"]]
            add(f"static constexpr uint8_t {fid}_SOURCE = SOURCE_{src};")
            if clear := field.get("clear"):
                x, y, w, h = (clear[k] for k in ("x", "y", "w", "h"))
                add(f"static constexpr Rect {fid}_CLEAR{{{x}, {y}, {w}, {h}}};")
            if fill := field.get("fill"):
                x, y, w, h = (fill[k] for k in ("x", "y", "w", "h"))
                add(f"static constexpr Rect {fid}_FILL{{{x}, {y}, {w}, {h}}};")
            if track := field.get("track"):
                x, y, w, h = (track[k] for k in ("x", "y", "w", "h"))
                add(f"static constexpr Rect {fid}_TRACK{{{x}, {y}, {w}, {h}}};")
            if anchor := field.get("anchor"):
                ax, ay = (anchor[k] for k in ("x", "y"))
                add(f"static constexpr Point {fid}_ANCHOR{{{ax}, {ay}}};")
            if align := field.get("align"):
                add(
                    f"static constexpr esphome::display::TextAlign {fid}_ALIGN = "
                    f"esphome::display::TextAlign::{ALIGN_MAP[align]};"
                )
            if fmt := field.get("format"):
                add(f"static constexpr const char *{fid}_FORMAT = {c_string(fmt)};")
        add("")

    add("// ---- fonts (defined by layout/generated/fonts.yaml) ----------")
    for font in cfg.get("fonts", []):
        add(f"//   id(font_{font['id']})  ->  size {font['size']}  ({font['file']})")
    add("")
    add("}  // namespace e1003")
    add("")

    return "\n".join(out)


def emit_fonts(cfg: dict) -> str:
    out = [
        "# AUTO GENERATED FILE -- DO NOT EDIT",
        "# source: layout/ui_layout.yaml   tool: tools/layout_to_h.py",
        "font:",
    ]
    for font in cfg["fonts"]:
        out.append(f"  - file: {font['file']}")
        out.append(f"    id: {font['id']}")
        out.append(f"    size: {font['size']}")
        out.append("")
    return "\n".join(out)


def emit_policy(cfg: dict) -> str:
    refresh = cfg["refresh"]
    canvas = cfg["meta"]["canvas"]
    return "\n".join(
        [
            "# AUTO GENERATED FILE -- DO NOT EDIT",
            "# source: layout/ui_layout.yaml   tool: tools/layout_to_h.py",
            "# Canvas size and refresh policy, pulled into the entry-point YAML as a",
            "# package. ESPHome merges substitutions declared by packages, so the",
            "# layout file stays the single source of truth for these values.",
            "substitutions:",
            f"  canvas_width: {canvas['width']}",
            f"  canvas_height: {canvas['height']}",
            f"  refresh_boot_mode: {refresh['boot_mode']}",
            f"  refresh_partial_mode: {refresh['partial_mode']}",
            f"  refresh_full_update_every: {refresh['full_update_every']}",
            f"  refresh_settle_delay: {refresh['settle_delay']}",
            f"  refresh_env_interval: {refresh['env_interval']}",
            "",
        ]
    )


# ---------------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------------
def print_map(cfg: dict) -> None:
    canvas = cfg["meta"]["canvas"]
    print(f"canvas: {canvas['width']} x {canvas['height']}\n")

    print("| zone | area (visual coords) | op | control | data |")
    print("|------|----------------------|----|---------|------|")
    for zone in cfg["zones"]:
        a = zone["area"]
        data = ", ".join(f"{k}={v}" for k, v in (zone.get("data") or {}).items()) or "-"
        print(
            f"| `{zone['id']}` | {a['x1']},{a['y1']} - {a['x2']},{a['y2']} | "
            f"{zone['op']} | {zone.get('control') or '-'} | {data} |"
        )

    print("\nruntime text entities (set these from Home Assistant):\n")
    print("| entity | default | purpose |")
    print("|--------|---------|---------|")
    message = cfg["runtime"].get("message", {}).get("text")
    if message:
        print(f"| `text.{message}` | local greeting | clock card message |")
    for control in cfg["runtime"].get("controls", []):
        print(f"| `text.{control['target']}` | ${control['id']} default | entity_id to control |")
        print(f"| `text.{control['action']}` | `light.turn_on` | action used by `call` zones |")
        print(f"| `text.{control['state']}` | compile-time binding | card state override |")
        print(f"| `text.{control['value']}` | compile-time binding | card value override |")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate only, write nothing")
    parser.add_argument("--print", dest="print_map", action="store_true", help="print the zone/entity map")
    args = parser.parse_args()

    cfg = yaml.safe_load(LAYOUT_FILE.read_text())

    if args.print_map:
        print_map(cfg)

    problems = validate(cfg)
    if problems:
        print(f"{LAYOUT_FILE.relative_to(REPO)}: {len(problems)} problem(s)", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print(f"layout OK: {len(cfg.get('zones', []))} zones, "
          f"{len(cfg.get('fonts', []))} fonts, "
          f"{sum(len(c.get('fields', [])) for c in cfg.get('cards', {}).values())} fields")

    if args.check:
        return 0

    GEN_DIR.mkdir(parents=True, exist_ok=True)
    HEADER_OUT.write_text(emit_header(cfg))
    FONTS_OUT.write_text(emit_fonts(cfg))
    POLICY_OUT.write_text(emit_policy(cfg))
    for path in (HEADER_OUT, FONTS_OUT, POLICY_OUT):
        print(f"  wrote {path.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())