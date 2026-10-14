#pragma once

// ============================================================
// AUTO GENERATED FILE -- DO NOT EDIT
//
// source : layout/ui_layout.yaml
// tool   : tools/layout_to_h.py
// built  : 2026-10-14 10:54:36
// ============================================================

#include <cstdint>
#include <cstddef>

namespace e1003 {

struct Rect { uint16_t x; uint16_t y; uint16_t w; uint16_t h; };
struct Area { uint16_t x1; uint16_t y1; uint16_t x2; uint16_t y2; };
struct Point { uint16_t x; uint16_t y; };

static constexpr uint16_t CANVAS_WIDTH = 1872;
static constexpr uint16_t CANVAS_HEIGHT = 1404;

// ---- static bitmap -------------------------------------------
static constexpr uint16_t BITMAP_WIDTH = 1872;
static constexpr uint16_t BITMAP_HEIGHT = 1404;

// ---- grayscale palette ---------------------------------------
static constexpr uint8_t G2 = 225;
static constexpr uint8_t G3 = 185;
static constexpr uint8_t G5 = 75;

// ---- refresh policy ------------------------------------------
// (the timing values live in layout/generated/policy.yaml and are
//  consumed by the YAML side, these are the GUI-safe constants)

// ---- field source kinds --------------------------------------
static constexpr uint8_t SOURCE_CLOCK = 0;
static constexpr uint8_t SOURCE_RTC = 1;
static constexpr uint8_t SOURCE_SENSOR = 2;
static constexpr uint8_t SOURCE_TEXT = 3;
static constexpr uint8_t SOURCE_LIGHT_STATE = 4;
static constexpr uint8_t SOURCE_LIGHT_VALUE = 5;

// ---- runtime control ids -------------------------------------
enum class ZoneOp : uint8_t { TOGGLE, CALL, SCRIPT };

struct Control { const char *id; };
static constexpr Control CONTROLS[] = {
  {"main_light"},
};
static constexpr size_t CONTROL_COUNT = 1;

// ---- touch zones ---------------------------------------------
struct Zone {
  const char *id;
  Area area;
  const char *control;
  ZoneOp op;
  const char *data_key;
  const char *data_value;
};

static constexpr Zone ZONES[] = {
  {"light_toggle", {1569, 513, 1774, 604}, "main_light", ZoneOp::TOGGLE, nullptr, nullptr},
  {"light_25", {1229, 711, 1346, 784}, "main_light", ZoneOp::CALL, "brightness_pct", "25"},
  {"light_50", {1359, 711, 1478, 784}, "main_light", ZoneOp::CALL, "brightness_pct", "50"},
  {"light_75", {1490, 711, 1607, 784}, "main_light", ZoneOp::CALL, "brightness_pct", "75"},
  {"light_100", {1620, 711, 1738, 784}, "main_light", ZoneOp::CALL, "brightness_pct", "100"},
};
static constexpr size_t ZONE_COUNT = 5;

// ---- card: clock ---------------------------------------
static constexpr Rect CLOCK_CLEAR{1516, 47, 312, 263};
static constexpr uint8_t CLOCK_DATE_SOURCE = SOURCE_CLOCK;
static constexpr Point CLOCK_DATE_ANCHOR{1802, 62};
static constexpr esphome::display::TextAlign CLOCK_DATE_ALIGN = esphome::display::TextAlign::TOP_RIGHT;
static constexpr const char *CLOCK_DATE_FORMAT = "%a, %b %d, %Y";
static constexpr uint8_t CLOCK_TIME_SOURCE = SOURCE_CLOCK;
static constexpr Point CLOCK_TIME_ANCHOR{1802, 125};
static constexpr esphome::display::TextAlign CLOCK_TIME_ALIGN = esphome::display::TextAlign::TOP_RIGHT;
static constexpr const char *CLOCK_TIME_FORMAT = "%H:%M";
static constexpr uint8_t CLOCK_MESSAGE_SOURCE = SOURCE_TEXT;
static constexpr Point CLOCK_MESSAGE_ANCHOR{1545, 256};
static constexpr esphome::display::TextAlign CLOCK_MESSAGE_ALIGN = esphome::display::TextAlign::TOP_LEFT;

// ---- card: environment ---------------------------------
static constexpr uint8_t ENV_TEMPERATURE_SOURCE = SOURCE_SENSOR;
static constexpr Rect ENV_TEMPERATURE_CLEAR{802, 518, 57, 56};
static constexpr Point ENV_TEMPERATURE_ANCHOR{830, 522};
static constexpr esphome::display::TextAlign ENV_TEMPERATURE_ALIGN = esphome::display::TextAlign::TOP_CENTER;
static constexpr const char *ENV_TEMPERATURE_FORMAT = "%.0f";
static constexpr uint8_t ENV_HUMIDITY_SOURCE = SOURCE_SENSOR;
static constexpr Rect ENV_HUMIDITY_CLEAR{1050, 518, 57, 56};
static constexpr Point ENV_HUMIDITY_ANCHOR{1078, 522};
static constexpr esphome::display::TextAlign ENV_HUMIDITY_ALIGN = esphome::display::TextAlign::TOP_CENTER;
static constexpr const char *ENV_HUMIDITY_FORMAT = "%.0f";

// ---- card: light ---------------------------------------
static constexpr uint8_t LIGHT_STATE_TEXT_SOURCE = SOURCE_LIGHT_STATE;
static constexpr Rect LIGHT_STATE_TEXT_CLEAR{1375, 550, 90, 55};
static constexpr Point LIGHT_STATE_TEXT_ANCHOR{1420, 554};
static constexpr esphome::display::TextAlign LIGHT_STATE_TEXT_ALIGN = esphome::display::TextAlign::TOP_CENTER;
static constexpr uint8_t LIGHT_BUTTON_SOURCE = SOURCE_LIGHT_STATE;
static constexpr Rect LIGHT_BUTTON_CLEAR{1569, 513, 205, 91};
static constexpr Rect LIGHT_BUTTON_FILL{1580, 525, 183, 67};
static constexpr Point LIGHT_BUTTON_ANCHOR{1671, 534};
static constexpr esphome::display::TextAlign LIGHT_BUTTON_ALIGN = esphome::display::TextAlign::TOP_CENTER;
static constexpr uint8_t LIGHT_VALUE_SOURCE = SOURCE_LIGHT_VALUE;
static constexpr Rect LIGHT_VALUE_CLEAR{1387, 673, 100, 36};
static constexpr Point LIGHT_VALUE_ANCHOR{1395, 673};
static constexpr esphome::display::TextAlign LIGHT_VALUE_ALIGN = esphome::display::TextAlign::TOP_LEFT;
static constexpr const char *LIGHT_VALUE_FORMAT = "%d%%";
static constexpr uint8_t LIGHT_BAR_SOURCE = SOURCE_LIGHT_VALUE;
static constexpr Rect LIGHT_BAR_CLEAR{1501, 674, 277, 45};
static constexpr Rect LIGHT_BAR_TRACK{1510, 686, 258, 20};

// ---- card: footer --------------------------------------
static constexpr uint8_t FOOTER_TIME_SOURCE = SOURCE_RTC;
static constexpr Rect FOOTER_TIME_CLEAR{1706, 1324, 56, 34};
static constexpr Point FOOTER_TIME_ANCHOR{1734, 1327};
static constexpr esphome::display::TextAlign FOOTER_TIME_ALIGN = esphome::display::TextAlign::TOP_CENTER;
static constexpr const char *FOOTER_TIME_FORMAT = "%H:%M";

// ---- fonts (defined by layout/generated/fonts.yaml) ----------
//   id(font_font_tiny)  ->  size 20  (${font_regular})
//   id(font_font_medium)  ->  size 36  (${font_bold})
//   id(font_font_large)  ->  size 48  (${font_bold})
//   id(font_font_number)  ->  size 110  (${font_bold})

}  // namespace e1003
