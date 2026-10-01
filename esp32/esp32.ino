/**
 * ==============================================================================
 * EchoSense ESP32 Sensing Unit Firmware (PlatformIO & Arduino C++)
 * ==============================================================================
 * HIGH-PERFORMANCE ACOUSTIC SENSING & PHYSICAL EMERGENCY SOS NODE
 * (100% STANDALONE - NO LINKED FILES)
 * 
 * Hardware Connections (Standard Conflict-Free Pins):
 * - INMP441 Microphone VDD      -> ESP32 3V3 (3.3V Clean Power - NEVER 5V!)
 * - INMP441 Microphone GND      -> ESP32 GND
 * - INMP441 Microphone L/R      -> ESP32 GND (Selects Left Audio Channel - NEVER float!)
 * - INMP441 Microphone SCK/BCLK -> ESP32 GPIO 14
 * - INMP441 Microphone WS/LRCK  -> ESP32 GPIO 25
 * - INMP441 Microphone SD/DIN   -> ESP32 GPIO 32
 * - 3-Pin SOS Button VCC        -> ESP32 3V3 (CRITICAL: NEVER 5V to protect GPIO!)
 * - 3-Pin SOS Button GND        -> ESP32 GND
 * - 3-Pin SOS Button SW1/Signal -> ESP32 GPIO 18
 * - Built-in Status LED         -> ESP32 GPIO 2
 */

#include <Arduino.h>
#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include <driver/i2s.h>

// ==============================================================================
// 1. CONFIGURATION (EDIT YOUR WI-FI CREDENTIALS & LAPTOP IP HERE)
// ==============================================================================
#define WIFI_SSID           "VijHouse-JioFiber-4G"
#define WIFI_PASSWORD       "mudit@9152787816"

#define BACKEND_HOST        "192.168.29.19"   // Laptop IPv4 address running EchoSense
#define BACKEND_PORT        8000

#define ESP32_DEVICE_ID     "ESP32_SENSE_01"
#define ESP32_API_KEY       "esp32_auth_token_9472e0a4f5b18"

// INMP441 I2S Digital Microphone Pinout (Standard Safe ESP32 Pins)
#define I2S_SCK_PIN         14  // Serial Clock (BCLK)
#define I2S_WS_PIN          25  // Word Select (LRCK)
#define I2S_SD_PIN          32  // Serial Data (DIN from Mic)
#define I2S_PORT            I2S_NUM_0

// Audio Sampling Specifications
#define SAMPLE_RATE         16000     // 16 kHz for YAMNet AI Classifier
#define CHUNK_SIZE_SAMPLES  800       // 50ms chunk (1600 bytes at 16-bit PCM)
#define DMA_BUF_COUNT       8
#define DMA_BUF_LEN         256

// Physical SOS Push Button Pinout & Timing
#define SOS_BUTTON_PIN      18    // Push Button Signal -> GPIO 18
#define BUTTON_AUTO_DETECT  true  // Auto-detect Active-LOW or Active-HIGH
#define BUTTON_ACTIVE_STATE LOW
#define DEBOUNCE_DELAY_MS   50    // Mechanical debounce time
#define SOS_COOLDOWN_MS     5000  // 5-second anti-bounce cooldown

// Telemetry & Indicators
#define HEARTBEAT_INTERVAL_MS 5000
#define STATUS_LED_PIN      2     // Built-in Blue LED

// ==============================================================================
// 2. HARDWARE DRIVERS & STATE VARIABLES
// ==============================================================================
WebSocketsClient webSocket;
bool isWsConnected = false;
unsigned long lastHeartbeatTime = 0;
unsigned long lastWifiCheckTime = 0;
unsigned long lastLedToggleTime = 0;

volatile bool rawButtonPressed = false;
bool sosArmed = true;
int buttonActiveState = BUTTON_ACTIVE_STATE;
unsigned long lastSosTriggerTime = 0;

int32_t raw_i2s_buffer[CHUNK_SIZE_SAMPLES];
int16_t pcm16_transmit_buffer[CHUNK_SIZE_SAMPLES];

// Function Prototypes
void setupI2S();
void setupWiFi();
void checkWiFiConnection();
void handleSosButton();
void updateStatusLed();
void sendHeartbeat();
void sendSosEvent();
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length);
void IRAM_ATTR onButtonInterrupt();

void IRAM_ATTR onButtonInterrupt() {
    rawButtonPressed = true;
}

// ==============================================================================
// 3. SETUP ENTRY POINT
// ==============================================================================
void setup() {
    Serial.begin(115200);
    delay(400);

    Serial.println("\n============================================");
    Serial.println("  ECHOSENSE ESP32 SENSING UNIT (STANDALONE) ");
    Serial.println("  Mic SCK=14, WS=25, SD=32 | SOS Button=18  ");
    Serial.println("============================================");

    pinMode(STATUS_LED_PIN, OUTPUT);
    digitalWrite(STATUS_LED_PIN, LOW); // LED OFF initially

    // Initialize Push Button with Auto-Polarity Detection
    pinMode(SOS_BUTTON_PIN, INPUT_PULLUP);
    delay(50);
    
    int idleVal = digitalRead(SOS_BUTTON_PIN);
    if (BUTTON_AUTO_DETECT) {
        if (idleVal == HIGH) {
            buttonActiveState = LOW;
            attachInterrupt(digitalPinToInterrupt(SOS_BUTTON_PIN), onButtonInterrupt, FALLING);
            Serial.println("[BUTTON] Detected: Active-LOW (Idle HIGH -> Pressed LOW)");
        } else {
            buttonActiveState = HIGH;
            attachInterrupt(digitalPinToInterrupt(SOS_BUTTON_PIN), onButtonInterrupt, RISING);
            Serial.println("[BUTTON] Detected: Active-HIGH (Idle LOW -> Pressed HIGH)");
        }
    } else {
        buttonActiveState = BUTTON_ACTIVE_STATE;
        attachInterrupt(digitalPinToInterrupt(SOS_BUTTON_PIN), onButtonInterrupt, (buttonActiveState == LOW) ? FALLING : RISING);
    }

    setupI2S();
    setupWiFi();

    // Initialize WebSocket connection to EchoSense Laptop Portal
    String wsUrl = "/ws/audio?token=" + String(ESP32_API_KEY);
    Serial.printf("[WS] Connecting to ws://%s:%d%s\n", BACKEND_HOST, BACKEND_PORT, wsUrl.c_str());
    webSocket.begin(BACKEND_HOST, BACKEND_PORT, wsUrl.c_str());
    webSocket.onEvent(webSocketEvent);
    webSocket.setReconnectInterval(2000);
    webSocket.enableHeartbeat(15000, 3000, 2);

    Serial.println("[ESP32] Sensing Unit fully initialized and running.");
}

// ==============================================================================
// 4. MAIN SUPERLOOP
// ==============================================================================
void loop() {
    webSocket.loop();
    checkWiFiConnection();
    handleSosButton();
    updateStatusLed();

    unsigned long currentMillis = millis();

    // 1. Send Periodic Health Heartbeat
    if (currentMillis - lastHeartbeatTime >= HEARTBEAT_INTERVAL_MS) {
        lastHeartbeatTime = currentMillis;
        sendHeartbeat();
    }

    // 2. Non-blocking Audio Acquisition & Streaming (50ms timeout prevents hangs)
    if (isWsConnected) {
        size_t bytes_read = 0;
        esp_err_t result = i2s_read(
            I2S_PORT,
            raw_i2s_buffer,
            sizeof(raw_i2s_buffer),
            &bytes_read,
            pdMS_TO_TICKS(50)
        );

        if (result == ESP_OK && bytes_read > 0) {
            int samples_read = bytes_read / sizeof(int32_t);
            for (int i = 0; i < samples_read; i++) {
                // INMP441 is 24-bit MSB-aligned in 32-bit slot (bits 31..8).
                // Apply clean +12dB room gain with saturation clamping to prevent
                // two's complement sign-bit wrap-around distortion!
                int32_t sample = raw_i2s_buffer[i] >> 14;
                if (sample > 32767) sample = 32767;
                else if (sample < -32768) sample = -32768;
                pcm16_transmit_buffer[i] = (int16_t)sample;
            }
            webSocket.sendBIN(
                (uint8_t*)pcm16_transmit_buffer,
                samples_read * sizeof(int16_t)
            );
        }
    } else {
        delay(10);
    }
}

// ==============================================================================
// 5. STATUS LED FEEDBACK
// ==============================================================================
void updateStatusLed() {
    unsigned long now = millis();
    if (!isWsConnected) {
        // Blink fast while disconnected / connecting
        if (now - lastLedToggleTime >= 250) {
            lastLedToggleTime = now;
            digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN));
        }
    } else {
        // Solid ON when streaming audio to backend
        digitalWrite(STATUS_LED_PIN, HIGH);
    }
}

// ==============================================================================
// 6. I2S MICROPHONE DRIVER SETUP
// ==============================================================================
void setupI2S() {
    Serial.println("[I2S] Configuring I2S DMA for INMP441 Microphone (16 kHz)...");
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = i2s_comm_format_t(I2S_COMM_FORMAT_STAND_I2S),
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = DMA_BUF_COUNT,
        .dma_buf_len = DMA_BUF_LEN,
        .use_apll = false,
        .tx_desc_auto_clear = false,
        .fixed_mclk = 0
    };

    i2s_pin_config_t pin_config = {
        .bck_io_num = I2S_SCK_PIN,
        .ws_io_num = I2S_WS_PIN,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = I2S_SD_PIN
    };

    esp_err_t err = i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
    if (err != ESP_OK) {
        Serial.printf("[I2S ERROR] Driver install failed: %d\n", err);
        return;
    }

    err = i2s_set_pin(I2S_PORT, &pin_config);
    if (err != ESP_OK) {
        Serial.printf("[I2S ERROR] Pin set failed: %d\n", err);
        return;
    }

    i2s_zero_dma_buffer(I2S_PORT);
    Serial.println("[I2S] INMP441 Microphone ready at 16000 Hz.");
}

// ==============================================================================
// 7. PHYSICAL SOS BUTTON HANDLER (DEBOUNCED & RE-ARMED)
// ==============================================================================
void handleSosButton() {
    unsigned long now = millis();
    if (rawButtonPressed) {
        rawButtonPressed = false;
        delay(DEBOUNCE_DELAY_MS);
        if (digitalRead(SOS_BUTTON_PIN) == buttonActiveState) {
            if (sosArmed && (now - lastSosTriggerTime >= SOS_COOLDOWN_MS)) {
                lastSosTriggerTime = now;
                sosArmed = false;
                Serial.println("\n🚨 [SOS] Physical button press confirmed! Triggering emergency alert!");
                sendSosEvent();
            }
        }
    }

    if (!sosArmed && (now - lastSosTriggerTime >= SOS_COOLDOWN_MS)) {
        if (digitalRead(SOS_BUTTON_PIN) != buttonActiveState) {
            sosArmed = true;
            Serial.println("[SOS] Cooldown ended. Emergency button re-armed.");
        }
    }
}

// ==============================================================================
// 8. WEBSOCKET EVENT DISPATCHER
// ==============================================================================
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    switch (type) {
        case WStype_DISCONNECTED:
            isWsConnected = false;
            Serial.println("[WS] Disconnected from EchoSense Backend.");
            break;
        case WStype_CONNECTED:
            isWsConnected = true;
            Serial.printf("✅ [WS] Connected to EchoSense Hub at %s:%d\n", BACKEND_HOST, BACKEND_PORT);
            sendHeartbeat();
            break;
        case WStype_TEXT:
            Serial.printf("[WS RX] Text message: %s\n", payload);
            break;
        default:
            break;
    }
}

// ==============================================================================
// 9. TELEMETRY & SOS TRANSMITTERS
// ==============================================================================
void sendSosEvent() {
    JsonDocument doc;
    doc["type"] = "SOS";
    doc["deviceId"] = ESP32_DEVICE_ID;
    doc["timestamp"] = millis();
    doc["source"] = "ESP32_PHYSICAL_BUTTON";

    String jsonString;
    serializeJson(doc, jsonString);
    webSocket.sendTXT(jsonString);
    Serial.println("[SOS] Sent emergency packet over WebSocket.");
}

void sendHeartbeat() {
    if (!isWsConnected) return;

    JsonDocument doc;
    doc["type"] = "HEARTBEAT";
    doc["deviceId"] = ESP32_DEVICE_ID;
    doc["rssi"] = WiFi.RSSI();
    doc["uptime"] = millis() / 1000;
    doc["firmwareVersion"] = "1.2.0";
    doc["sensors"]["inmp441"] = "STREAMING";
    doc["sensors"]["sosButton"] = sosArmed ? "READY" : "COOLDOWN";
    doc["status"] = "ONLINE";

    String jsonString;
    serializeJson(doc, jsonString);
    webSocket.sendTXT(jsonString);
}

// ==============================================================================
// 10. WI-FI MANAGER
// ==============================================================================
void setupWiFi() {
    Serial.printf("[WiFi] Connecting to %s ", WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 25) {
        delay(400);
        Serial.print(".");
        digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN));
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\n✅ [WiFi] Connected! IP Address: %s (RSSI: %d dBm)\n",
                      WiFi.localIP().toString().c_str(), WiFi.RSSI());
        digitalWrite(STATUS_LED_PIN, HIGH);
    } else {
        Serial.println("\n⚠️ [WiFi WARNING] Initial connection timed out. Will retry in background.");
    }
}

void checkWiFiConnection() {
    unsigned long now = millis();
    if (now - lastWifiCheckTime >= 6000) {
        lastWifiCheckTime = now;
        if (WiFi.status() != WL_CONNECTED) {
            Serial.println("[WiFi] Connection lost. Attempting reconnection...");
            WiFi.reconnect();
        }
    }
}
