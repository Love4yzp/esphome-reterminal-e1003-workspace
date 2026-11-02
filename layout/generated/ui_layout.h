#pragma once

// ============================================================
// AUTO GENERATED FILE -- DO NOT EDIT
//
// source : layout/ui_layout.yaml
// tool   : tools/layout_to_h.py
// built  : 2026-11-01 23:46:34
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

enum class ZoneOp : uint8_t { TOGGLE, CALL, SCRIPT };

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
  {"light_off", {1507, 508, 1643, 587}, "main_light", ZoneOp::CALL, "state", "off"},
  {"light_on", {1644, 508, 1781, 587}, "main_light", ZoneOp::CALL, "state", "on"},
  {"light_25", {1245, 681, 1369, 756}, "main_light", ZoneOp::CALL, "brightness_pct", "25"},
  {"light_50", {1385, 681, 1509, 756}, "main_light", ZoneOp::CALL, "brightness_pct", "50"},
  {"light_75", {1524, 681, 1648, 756}, "main_light", ZoneOp::CALL, "brightness_pct", "75"},
  {"light_100", {1664, 681, 1806, 756}, "main_light", ZoneOp::CALL, "brightness_pct", "100"},
};
static constexpr size_t ZONE_COUNT = 6;

// ---- card: network -------------------------------------
static constexpr uint8_t NETWORK_STATUS_SOURCE = SOURCE_TEXT;
static constexpr Rect NETWORK_STATUS_CLEAR{1527, 65, 278, 69};
static constexpr Point NETWORK_STATUS_ANCHOR{1531, 72};
static constexpr esphome::display::TextAlign NETWORK_STATUS_ALIGN = esphome::display::TextAlign::TOP_LEFT;
static constexpr uint8_t NETWORK_ROLE_SOURCE = SOURCE_TEXT;
static constexpr Rect NETWORK_ROLE_CLEAR{1578, 171, 205, 23};
static constexpr Point NETWORK_ROLE_ANCHOR{1578, 171};
static constexpr esphome::display::TextAlign NETWORK_ROLE_ALIGN = esphome::display::TextAlign::TOP_LEFT;
static constexpr uint8_t NETWORK_NAME_SOURCE = SOURCE_TEXT;
static constexpr Rect NETWORK_NAME_CLEAR{1578, 197, 205, 29};
static constexpr Point NETWORK_NAME_ANCHOR{1578, 197};
static constexpr esphome::display::TextAlign NETWORK_NAME_ALIGN = esphome::display::TextAlign::TOP_LEFT;
static constexpr uint8_t NETWORK_DETAIL_SOURCE = SOURCE_TEXT;
static constexpr Rect NETWORK_DETAIL_CLEAR{1578, 253, 210, 31};
static constexpr Point NETWORK_DETAIL_ANCHOR{1578, 253};
static constexpr esphome::display::TextAlign NETWORK_DETAIL_ALIGN = esphome::display::TextAlign::TOP_LEFT;

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
static constexpr uint8_t LIGHT_STATE_CONTROL_SOURCE = SOURCE_LIGHT_STATE;
static constexpr Rect LIGHT_STATE_CONTROL_CLEAR{1503, 504, 282, 88};
static constexpr Rect LIGHT_STATE_CONTROL_TRACK{1507, 508, 274, 79};
static constexpr uint8_t LIGHT_OFF_LABEL_SOURCE = SOURCE_LIGHT_STATE;
static constexpr Point LIGHT_OFF_LABEL_ANCHOR{1575, 548};
static constexpr esphome::display::TextAlign LIGHT_OFF_LABEL_ALIGN = esphome::display::TextAlign::CENTER;
static constexpr uint8_t LIGHT_ON_LABEL_SOURCE = SOURCE_LIGHT_STATE;
static constexpr Point LIGHT_ON_LABEL_ANCHOR{1713, 548};
static constexpr esphome::display::TextAlign LIGHT_ON_LABEL_ALIGN = esphome::display::TextAlign::CENTER;
static constexpr uint8_t LIGHT_CURRENT_SOURCE = SOURCE_LIGHT_VALUE;
static constexpr Rect LIGHT_CURRENT_CLEAR{1644, 648, 162, 30};
static constexpr Point LIGHT_CURRENT_ANCHOR{1806, 650};
static constexpr esphome::display::TextAlign LIGHT_CURRENT_ALIGN = esphome::display::TextAlign::TOP_RIGHT;
static constexpr uint8_t LIGHT_PRESET_25_SOURCE = SOURCE_LIGHT_VALUE;
static constexpr Rect LIGHT_PRESET_25_CLEAR{1242, 678, 130, 82};
static constexpr Rect LIGHT_PRESET_25_TRACK{1245, 681, 124, 75};
static constexpr uint8_t LIGHT_PRESET_25_LABEL_SOURCE = SOURCE_LIGHT_VALUE;
static constexpr Point LIGHT_PRESET_25_LABEL_ANCHOR{1307, 719};
static constexpr esphome::display::TextAlign LIGHT_PRESET_25_LABEL_ALIGN = esphome::display::TextAlign::CENTER;
static constexpr uint8_t LIGHT_PRESET_50_SOURCE = SOURCE_LIGHT_VALUE;
static constexpr Rect LIGHT_PRESET_50_CLEAR{1382, 678, 130, 82};
static constexpr Rect LIGHT_PRESET_50_TRACK{1385, 681, 124, 75};
static constexpr uint8_t LIGHT_PRESET_50_LABEL_SOURCE = SOURCE_LIGHT_VALUE;
static constexpr Point LIGHT_PRESET_50_LABEL_ANCHOR{1447, 719};
static constexpr esphome::display::TextAlign LIGHT_PRESET_50_LABEL_ALIGN = esphome::display::TextAlign::CENTER;
static constexpr uint8_t LIGHT_PRESET_75_SOURCE = SOURCE_LIGHT_VALUE;
static constexpr Rect LIGHT_PRESET_75_CLEAR{1521, 678, 130, 82};
static constexpr Rect LIGHT_PRESET_75_TRACK{1524, 681, 124, 75};
static constexpr uint8_t LIGHT_PRESET_75_LABEL_SOURCE = SOURCE_LIGHT_VALUE;
static constexpr Point LIGHT_PRESET_75_LABEL_ANCHOR{1586, 719};
static constexpr esphome::display::TextAlign LIGHT_PRESET_75_LABEL_ALIGN = esphome::display::TextAlign::CENTER;
static constexpr uint8_t LIGHT_PRESET_100_SOURCE = SOURCE_LIGHT_VALUE;
static constexpr Rect LIGHT_PRESET_100_CLEAR{1661, 678, 148, 82};
static constexpr Rect LIGHT_PRESET_100_TRACK{1664, 681, 142, 75};
static constexpr uint8_t LIGHT_PRESET_100_LABEL_SOURCE = SOURCE_LIGHT_VALUE;
static constexpr Point LIGHT_PRESET_100_LABEL_ANCHOR{1735, 719};
static constexpr esphome::display::TextAlign LIGHT_PRESET_100_LABEL_ALIGN = esphome::display::TextAlign::CENTER;
static constexpr uint8_t LIGHT_BAR_SOURCE = SOURCE_LIGHT_VALUE;
static constexpr Rect LIGHT_BAR_CLEAR{1242, 780, 567, 45};
static constexpr Rect LIGHT_BAR_TRACK{1245, 783, 561, 39};

// ---- card: footer --------------------------------------
static constexpr uint8_t FOOTER_TIME_SOURCE = SOURCE_RTC;
static constexpr Rect FOOTER_TIME_CLEAR{1706, 1324, 56, 34};
static constexpr Point FOOTER_TIME_ANCHOR{1734, 1327};
static constexpr esphome::display::TextAlign FOOTER_TIME_ALIGN = esphome::display::TextAlign::TOP_CENTER;
static constexpr const char *FOOTER_TIME_FORMAT = "%H:%M";

// ---- fonts (defined by layout/generated/fonts.yaml) ----------
//   id(font_font_tiny)  ->  size 20  (${font_regular})
//   id(font_font_small)  ->  size 24  (${font_regular})
//   id(font_font_medium)  ->  size 36  (${font_bold})
//   id(font_font_large)  ->  size 48  (${font_bold})

}  // namespace e1003
