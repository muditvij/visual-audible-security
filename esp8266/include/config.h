/**
 * EchoSense ESP8266 Alert Unit Hardware & Network Configuration
 * Simplified & 100% Reliable:
 * - 16-pin LCD completely removed (eliminating wire clutter and boot hangs).
 * - Standard, non-boot-strapping GPIOs used exclusively:
 *   * Buzzer: D1 (GPIO 5)
 *   * WS2812 RGB Ring: D2 (GPIO 4)
 */
#ifndef ECHOSENSE_ESP8266_CONFIG_H
#define ECHOSENSE_ESP8266_CONFIG_H

// WiFi Configuration
#define WIFI_SSID           "VijHouse-JioFiber-4G"
#define WIFI_PASSWORD       "mudit@9152787816"

// Laptop Intelligence Hub Configuration
#define BACKEND_HOST        "192.168.29.19"   // IP Address of laptop running EchoSense backend
#define BACKEND_PORT        8000
#define ESP8266_DEVICE_ID   "ESP8266_ALERT_01"
#define ESP8266_API_KEY     "esp8266_auth_token_38c92a17df40c"

// Standard Safe Alert Hardware Pins (Zero Boot Conflicts)
// NodeMCU D1 = GPIO 5 (Safe general-purpose pin, standard I2C SCL)
// NodeMCU D2 = GPIO 4 (Safe general-purpose pin, standard I2C SDA)
#define BUZZER_PIN          5   // NodeMCU D1 (GPIO 5) -> Connect to Signal/IP on Buzzer Module
#define BUZZER_ACTIVE_LOW   false // false = Active-HIGH (standard); true = Active-LOW modules

#define RGB_RING_PIN        4   // NodeMCU D2 (GPIO 4) -> Connect to DI (Data In) on WS2812 Ring
#define RGB_PIXEL_COUNT     16  // Standard 16-LED NeoPixel ring (or adjust to your ring count)
#define RGB_BRIGHTNESS_CAP  150 // Power safety cap (0-255)

// Status LED (Onboard NodeMCU Blue LED)
#define STATUS_LED_PIN      2   // D4 / GPIO 2 (Active-LOW onboard LED)

// Timers
#define HEARTBEAT_INTERVAL_MS 5000
#define OFFLINE_TIMEOUT_MS    15000

#endif // ECHOSENSE_ESP8266_CONFIG_H
