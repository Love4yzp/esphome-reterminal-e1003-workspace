#pragma once

#include <cstdint>
#include <cstdio>

#include "esp_err.h"
#include "nvs.h"

#include "esphome/core/log.h"

namespace e1003 {

static const char *const SYSTEM_TAG = "e1003.system";

// ESPHome 2026.10.1 uses this fixed preference key when station credentials
// are provisioned at runtime instead of compiled into the firmware. The
// adjacent key stores optional fast-connect metadata. Keep these in sync with
// WiFiComponent::start() when upgrading the pinned ESPHome version.
static constexpr uint32_t WIFI_SETTINGS_PREFERENCE_KEY = 88491487UL;
static constexpr uint32_t WIFI_FAST_CONNECT_PREFERENCE_KEY =
    WIFI_SETTINGS_PREFERENCE_KEY + 1;

inline bool erase_nvs_key(nvs_handle_t handle, uint32_t preference_key) {
  char key[11];
  std::snprintf(key, sizeof(key), "%u",
                static_cast<unsigned>(preference_key));

  const esp_err_t result = nvs_erase_key(handle, key);
  if (result == ESP_OK || result == ESP_ERR_NVS_NOT_FOUND) {
    return true;
  }

  ESP_LOGE(SYSTEM_TAG, "Could not erase Wi-Fi preference %s: %s", key,
           esp_err_to_name(result));
  return false;
}

inline bool clear_wifi_credentials() {
  nvs_handle_t handle;
  const esp_err_t open_result =
      nvs_open("esphome", NVS_READWRITE, &handle);
  if (open_result != ESP_OK) {
    ESP_LOGE(SYSTEM_TAG, "Could not open ESPHome preferences: %s",
             esp_err_to_name(open_result));
    return false;
  }

  const bool credentials_erased =
      erase_nvs_key(handle, WIFI_SETTINGS_PREFERENCE_KEY);
  const bool fast_connect_erased =
      erase_nvs_key(handle, WIFI_FAST_CONNECT_PREFERENCE_KEY);
  const esp_err_t commit_result = nvs_commit(handle);
  nvs_close(handle);

  if (!credentials_erased || !fast_connect_erased ||
      commit_result != ESP_OK) {
    if (commit_result != ESP_OK) {
      ESP_LOGE(SYSTEM_TAG, "Could not commit Wi-Fi reset: %s",
               esp_err_to_name(commit_result));
    }
    return false;
  }

  ESP_LOGI(SYSTEM_TAG,
           "Saved Wi-Fi credentials cleared; other settings were preserved");
  return true;
}

}  // namespace e1003
