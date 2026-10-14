#pragma once
// =============================================================================
// E1003 render helpers
// =============================================================================
// C++ that would be pure noise inside a YAML lambda lives here instead.
// This header is listed in `esphome.includes:` (packages/core.yaml) and is
// included at the end of the generated main.cpp, after `esphome.h`.
//
// The bitmap header is flattened into the same build src/ directory, hence the
// basename include below.
// =============================================================================

#include "dashboard_static_v4.h"

namespace e1003 {

/// Paint the PackBits-RLE 4bpp grayscale bitmap over the whole panel.
///
/// The design PNG is encoded as "one byte = two horizontally adjacent pixels,
/// high nibble first" (see tools/png_to_h.py). Runs are encoded exactly like
/// PackBits: `n <= 127` means `n + 1` literal bytes follow, `n >= 129` means
/// `257 - n` copies of the next byte follow, `128` is a no-op.
inline void draw_rle_bitmap(esphome::display::Display &disp) {
  int src_i = 0;
  int packed_index = 0;

  auto emit_byte = [&](uint8_t packed) {
    const int pixel_index = packed_index * 2;
    const int y = pixel_index / DASHBOARD_V4_WIDTH;
    const int x = pixel_index - y * DASHBOARD_V4_WIDTH;

    const uint8_t hi = (packed >> 4) & 0x0F;
    const uint8_t lo = packed & 0x0F;

    disp.draw_pixel_at(x, y, esphome::Color(uint8_t(hi * 17), uint8_t(hi * 17), uint8_t(hi * 17)));
    if (x + 1 < DASHBOARD_V4_WIDTH) {
      disp.draw_pixel_at(x + 1, y, esphome::Color(uint8_t(lo * 17), uint8_t(lo * 17), uint8_t(lo * 17)));
    }
    packed_index++;
  };

  while (src_i < DASHBOARD_V4_RLE_SIZE && packed_index < DASHBOARD_V4_RAW_SIZE) {
    const uint8_t code = dashboard_v4_rle[src_i++];

    if (code <= 127) {
      const int count = code + 1;
      for (int i = 0; i < count; i++) {
        emit_byte(dashboard_v4_rle[src_i++]);
      }
    } else if (code >= 129) {
      const int count = 257 - code;
      const uint8_t value = dashboard_v4_rle[src_i++];
      for (int i = 0; i < count; i++) {
        emit_byte(value);
      }
    }
  }
}

}  // namespace e1003