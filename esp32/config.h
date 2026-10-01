/**
 * EchoSense ESP32 Sensing Unit Hardware & Network Configuration
 */
#ifndef ECHOSENSE_ESP32_CONFIG_H
#define ECHOSENSE_ESP32_CONFIG_H

// WiFi Credentials
#define WIFI_SSID           "VijHouse-JioFiber-4G"
#define WIFI_PASSWORD       "mudit@9152787816"

// Laptop Intelligence Hub Configuration
#define BACKEND_HOST        "192.168.29.19"   // IP Address of laptop running EchoSense backend
#define BACKEND_PORT        8000
#define ESP32_DEVICE_ID     "ESP32_SENSE_01"
#define ESP32_API_KEY       "esp32_auth_token_9472e0a4f5b18"

// INMP441 I2S Digital Microphone Pinout
#define I2S_SCK_PIN         14  // Serial Clock (BCLK)
#define I2S_WS_PIN          25  // Word Select (LRCK / Left-Right Clock)
#define I2S_SD_PIN          32  // Serial Data (DIN from Mic)
#define I2S_PORT            I2S_NUM_0

// Audio Sampling Specifications
#define SAMPLE_RATE         16000     // 16 kHz for YAMNet
#define CHUNK_SIZE_SAMPLES  800       // 50ms chunk (1600 bytes at 16-bit)
#define DMA_BUF_COUNT       8
#define DMA_BUF_LEN         256

// Physical SOS Push Button Pinout & Timing (3-Pin Module: GND, VCC, SW1)
#define SOS_BUTTON_PIN          18    // Connect to SW1 on button module
#define BUTTON_AUTO_DETECT      true  // Automatically detects Active-LOW or Active-HIGH on boot
#define BUTTON_ACTIVE_STATE     LOW   // Fallback: LOW if SW1 pulls to GND on press; HIGH if SW1 pulls to VCC
#define DEBOUNCE_DELAY_MS       50    // Mechanical contact debounce
#define SOS_COOLDOWN_MS         5000  // Anti-spam cooldown latch

// Telemetry & Watchdog Timers
#define HEARTBEAT_INTERVAL_MS   5000
#define STATUS_LED_PIN          2     // Built-in Blue LED

#endif // ECHOSENSE_ESP32_CONFIG_H
