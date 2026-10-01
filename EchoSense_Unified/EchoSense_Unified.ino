/**
 * ==============================================================================
 * EchoSense Unified Single-File Firmware for ESP32 & ESP8266
 * ==============================================================================
 * ONE SINGLE FILE FOR BOTH HARDWARE UNITS - NO SEPARATE LINKED FILES!
 *
 * How to Upload:
 * 1. Open this file in Arduino IDE.
 * 2. To flash the SENSING UNIT (ESP32):
 *    - Connect ESP32 via Micro-USB Data Cable.
 *    - Select: Tools -> Board -> "ESP32 Dev Module" (or "DOIT ESP32 DEVKIT V1")
 *    - Select your ESP32 COM port and click Upload!
 *    - The compiler automatically compiles the INMP441 Audio Streaming & SOS firmware.
 *
 * 3. To flash the ALERT UNIT (ESP8266):
 *    - Connect NodeMCU ESP8266 via Micro-USB Data Cable.
 *    - Select: Tools -> Board -> "NodeMCU 1.0 (ESP-12E Module)" (or "Generic ESP8266")
 *    - Select your ESP8266 COM port and click Upload!
 *    - The compiler automatically compiles the WS2812 RGB Ring & Acoustic Buzzer firmware.
 *
 * Libraries Required (Install in Arduino IDE Library Manager):
 * - "Adafruit NeoPixel" by Adafruit
 * - "WebSockets" by Markus Sattler (links2004)
 * - "ArduinoJson" by Benoit Blanchon (v7.x or v6.x)
 *
 * Standard Safe Conflict-Free Pins:
 * - ESP32:   SCK=14, WS=25, SD=32, SOS Button=18, Status LED=2
 * - ESP8266: Buzzer=D1 (GPIO 5), WS2812 RGB Ring=D2 (GPIO 4), Status LED=D4 (GPIO 2)
 */

// ==============================================================================
// 1. SHARED NETWORK & BACKEND SETTINGS (EDIT YOUR WI-FI CREDENTIALS HERE)
// ==============================================================================
#define WIFI_SSID           "VijHouse-JioFiber-4G"
#define WIFI_PASSWORD       "mudit@9152787816"

#define BACKEND_HOST        "192.168.29.19"   // IP Address of laptop running EchoSense portal
#define BACKEND_PORT        8000

// Device Auth Tokens
#define ESP32_DEVICE_ID     "ESP32_SENSE_01"
#define ESP32_API_KEY       "esp32_auth_token_9472e0a4f5b18"

#define ESP8266_DEVICE_ID   "ESP8266_ALERT_01"
#define ESP8266_API_KEY     "esp8266_auth_token_38c92a17df40c"

#define HEARTBEAT_INTERVAL_MS 5000


// ==============================================================================
// 2. ESP32 SENSING UNIT CODE (COMPILES AUTOMATICALLY WHEN ESP32 IS SELECTED)
// ==============================================================================
#if defined(ESP32)

#include <Arduino.h>
#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include <driver/i2s.h>

// Standard Safe Pins for ESP32 DevKit
#define I2S_SCK_PIN         14    // Serial Clock (BCLK) -> INMP441 SCK
#define I2S_WS_PIN          25    // Word Select (LRCK)  -> INMP441 WS
#define I2S_SD_PIN          32    // Serial Data (DIN)   -> INMP441 SD
#define I2S_PORT            I2S_NUM_0

#define SOS_BUTTON_PIN      18    // Push Button Signal  -> SW1/OUT
#define BUTTON_AUTO_DETECT  true  // Auto-detect Active-LOW or Active-HIGH
#define BUTTON_ACTIVE_STATE LOW
#define DEBOUNCE_DELAY_MS   50    // Mechanical debounce
#define SOS_COOLDOWN_MS     5000  // 5s anti-bounce cooldown
#define STATUS_LED_PIN      2     // Built-in Blue LED

#define SAMPLE_RATE         16000
#define CHUNK_SIZE_SAMPLES  800   // 50ms chunks (1600 bytes)
#define DMA_BUF_COUNT       8
#define DMA_BUF_LEN         256

// State & Buffers
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

void setupI2S();
void setupWiFi();
void checkWiFiConnection();
void handleSosButton();
void updateStatusLed();
void sendHeartbeat();
void sendSosEvent();
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length);

void IRAM_ATTR onButtonInterrupt() {
    rawButtonPressed = true;
}

void setup() {
    Serial.begin(115200);
    delay(400);
    Serial.println("\n=================================================");
    Serial.println("  ECHOSENSE ESP32 SENSING UNIT INITIALIZING     ");
    Serial.println("  (Standard Pins: SCK=14, WS=25, SD=32, SOS=18) ");
    Serial.println("=================================================");

    pinMode(STATUS_LED_PIN, OUTPUT);
    digitalWrite(STATUS_LED_PIN, LOW);

    // Auto-detect button polarity
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

    String wsUrl = "/ws/audio?token=" + String(ESP32_API_KEY);
    Serial.printf("[WS] Connecting to ws://%s:%d%s\n", BACKEND_HOST, BACKEND_PORT, wsUrl.c_str());
    webSocket.begin(BACKEND_HOST, BACKEND_PORT, wsUrl.c_str());
    webSocket.onEvent(webSocketEvent);
    webSocket.setReconnectInterval(2000);
    webSocket.enableHeartbeat(15000, 3000, 2);

    Serial.println("[ESP32] Sensing Unit Ready.");
}

void loop() {
    webSocket.loop();
    checkWiFiConnection();
    handleSosButton();
    updateStatusLed();

    unsigned long currentMillis = millis();

    // 1. Periodic Telemetry Heartbeat
    if (currentMillis - lastHeartbeatTime >= HEARTBEAT_INTERVAL_MS) {
        lastHeartbeatTime = currentMillis;
        sendHeartbeat();
    }

    // 2. Non-blocking Audio Stream (50ms timeout prevents hangs if mic is disconnected)
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
            webSocket.sendBIN((uint8_t*)pcm16_transmit_buffer, samples_read * sizeof(int16_t));
        }
    } else {
        delay(10);
    }
}

void updateStatusLed() {
    unsigned long now = millis();
    if (!isWsConnected) {
        if (now - lastLedToggleTime >= 250) {
            lastLedToggleTime = now;
            digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN));
        }
    } else {
        digitalWrite(STATUS_LED_PIN, HIGH);
    }
}

void setupI2S() {
    Serial.println("[I2S] Initializing INMP441 Microphone (16 kHz)...");
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

    i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
    i2s_set_pin(I2S_PORT, &pin_config);
    i2s_zero_dma_buffer(I2S_PORT);
    Serial.println("[I2S] INMP441 Driver Installed.");
}

void handleSosButton() {
    unsigned long now = millis();
    if (rawButtonPressed) {
        rawButtonPressed = false;
        delay(DEBOUNCE_DELAY_MS);
        if (digitalRead(SOS_BUTTON_PIN) == buttonActiveState) {
            if (sosArmed && (now - lastSosTriggerTime >= SOS_COOLDOWN_MS)) {
                lastSosTriggerTime = now;
                sosArmed = false;
                Serial.println("\n🚨 [SOS] Physical button triggered!");
                sendSosEvent();
            }
        }
    }

    if (!sosArmed && (now - lastSosTriggerTime >= SOS_COOLDOWN_MS)) {
        if (digitalRead(SOS_BUTTON_PIN) != buttonActiveState) {
            sosArmed = true;
            Serial.println("[SOS] Button re-armed.");
        }
    }
}

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    switch (type) {
        case WStype_DISCONNECTED:
            isWsConnected = false;
            Serial.println("[WS] Disconnected from Backend.");
            break;
        case WStype_CONNECTED:
            isWsConnected = true;
            Serial.println("✅ [WS] Connected to EchoSense Portal!");
            sendHeartbeat();
            break;
        default:
            break;
    }
}

void sendSosEvent() {
    JsonDocument doc;
    doc["type"] = "SOS";
    doc["deviceId"] = ESP32_DEVICE_ID;
    doc["timestamp"] = millis();
    doc["source"] = "ESP32_PHYSICAL_BUTTON";

    String jsonString;
    serializeJson(doc, jsonString);
    webSocket.sendTXT(jsonString);
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
        Serial.printf("\n✅ [WiFi] Connected! IP: %s (RSSI: %d dBm)\n",
                      WiFi.localIP().toString().c_str(), WiFi.RSSI());
        digitalWrite(STATUS_LED_PIN, HIGH);
    } else {
        Serial.println("\n⚠️ [WiFi] Timeout. Retrying in background.");
    }
}

void checkWiFiConnection() {
    unsigned long now = millis();
    if (now - lastWifiCheckTime >= 6000) {
        lastWifiCheckTime = now;
        if (WiFi.status() != WL_CONNECTED) {
            WiFi.reconnect();
        }
    }
}

#endif // ESP32


// ==============================================================================
// 3. ESP8266 ALERT UNIT CODE (COMPILES AUTOMATICALLY WHEN ESP8266 IS SELECTED)
// ==============================================================================
#if defined(ESP8266)

#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include <Adafruit_NeoPixel.h>

// Standard Safe Pins for NodeMCU ESP8266 (Zero Boot Conflicts)
#define BUZZER_PIN          5   // NodeMCU D1 (GPIO 5) -> Connect to Signal/IP on Buzzer Module
#define BUZZER_ACTIVE_LOW   false

#define RGB_RING_PIN        4   // NodeMCU D2 (GPIO 4) -> Connect to DI (Data In) on WS2812 Ring
#define RGB_PIXEL_COUNT     16  // Standard 16-LED NeoPixel ring
#define STATUS_LED_PIN      2   // NodeMCU D4 (GPIO 2) -> Onboard Blue LED

#define OFFLINE_TIMEOUT_MS  15000

// ==============================================================================
// 3.1 HARDWARE DRIVERS & SMOOTH TRANSITION STATE
// ==============================================================================
Adafruit_NeoPixel strip(RGB_PIXEL_COUNT, RGB_RING_PIN, NEO_GRB + NEO_KHZ800);
WebSocketsClient webSocket;
bool isWsConnected = false;

unsigned long lastPacketReceivedTime = 0;
unsigned long lastHeartbeatTime = 0;
unsigned long lastWifiCheckTime = 0;
unsigned long lastStatusLedToggle = 0;
unsigned long lastAnimUpdate = 0;

int currentPriority = 4; // 0=SOS, 1=CRITICAL, 2=WARNING, 3=INFO, 4=NORMAL
String currentDisplayLabel = "System Ready";
String currentRgbMode = "WHITE_BREATH";
String currentBuzzerPattern = "OFF";

// High-Precision Smooth Color Lerp & Transition Engine
float currentR = 255.0f, currentG = 255.0f, currentB = 255.0f; // Pure ambient white on silence / normal
float targetR  = 255.0f, targetG  = 255.0f, targetB  = 255.0f; // Target color from AI Hub
float currentBrightness = 90.0f;
float targetBrightness  = 90.0f;
float animPhase = 0.0f;

bool buzzerState = false;

// Function Prototypes
void setupHardwareTest();
void setupWiFi();
void checkWiFiConnection();
void setSystemState(int priority, const String& label, const String& rgbMode, uint8_t r, uint8_t g, uint8_t b, const String& buzzer, bool isAcknowledge = false);
void updateRgbAnimation();
void updateBuzzerPattern();
void setBuzzerSound(bool on, int freq = 2400);
void updateStatusLed();
void sendHeartbeat();
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length);
uint8_t gammaCorrect(float val, float brightness, float mod = 1.0f);

// ==============================================================================
// 3.2 SOUND DRIVER
// ==============================================================================
void setBuzzerSound(bool on, int freq) {
    if (on) {
        if (BUZZER_ACTIVE_LOW) {
            digitalWrite(BUZZER_PIN, LOW);
        } else {
            tone(BUZZER_PIN, freq);
            digitalWrite(BUZZER_PIN, HIGH);
        }
    } else {
        noTone(BUZZER_PIN);
        digitalWrite(BUZZER_PIN, BUZZER_ACTIVE_LOW ? HIGH : LOW);
    }
}

// ==============================================================================
// 3.3 PERCEPTUAL GAMMA CORRECTION HELPER
// ==============================================================================
uint8_t gammaCorrect(float val, float brightness, float mod) {
    float norm = (val / 255.0f) * (brightness / 255.0f) * mod;
    if (norm <= 0.001f) return 0;
    if (norm >= 1.0f) return 255;
    // Perceptual quadratic gamma curve prevents harsh color-stepping
    return (uint8_t)(norm * norm * 255.0f + 0.5f);
}

// ==============================================================================
// 3.4 HARDWARE SELF-TEST WITH SMOOTH COLOR SWEEP
// ==============================================================================
void setupHardwareTest() {
    Serial.println("\n[HARDWARE TEST] Running smooth NeoPixel color verification sweep...");
    strip.begin();
    strip.setBrightness(140);

    // Smooth test sweep through primary alert spectrum
    uint32_t testColors[] = {
        strip.Color(255, 10, 10),   // Critical Red
        strip.Color(255, 160, 0),   // Warning Amber
        strip.Color(0, 220, 255),   // Domestic Cyan
        strip.Color(175, 55, 255),  // Info Violet
        strip.Color(255, 255, 255)  // Normal Pure White (Ambient Silence)
    };

    for (int c = 0; c < 5; c++) {
        for (int i = 0; i < RGB_PIXEL_COUNT; i++) {
            strip.setPixelColor(i, testColors[c]);
        }
        strip.show();
        delay(70);
    }

    // Startup dual-tone chirp
    setBuzzerSound(true, 2400);
    delay(100);
    setBuzzerSound(false);
    delay(60);
    setBuzzerSound(true, 3200);
    delay(120);
    setBuzzerSound(false);

    Serial.println("[HARDWARE TEST] WS2812 Ring and Buzzer operational!");
}

// ==============================================================================
// 3.5 SETUP ENTRY POINT
// ==============================================================================
void setup() {
    Serial.begin(115200);
    delay(300);
    Serial.println("\n=================================================");
    Serial.println("   ECHOSENSE ESP8266 ALERT UNIT INITIALIZING    ");
    Serial.println("   (Pins: D1=Buzzer, D2=WS2812 RGB Ring)       ");
    Serial.println("   Smooth Transition & Full-Spectrum Lighting    ");
    Serial.println("=================================================");

    pinMode(STATUS_LED_PIN, OUTPUT);
    digitalWrite(STATUS_LED_PIN, HIGH); // OFF initially (Active-LOW)

    pinMode(BUZZER_PIN, OUTPUT);
    setBuzzerSound(false);

    setupHardwareTest();

    setSystemState(4, "Connecting Wi-Fi...", "YELLOW_PULSE", 255, 180, 0, "OFF");

    setupWiFi();

    String wsUrl = "/ws/esp8266?token=" + String(ESP8266_API_KEY);
    Serial.printf("[WS] Connecting to ws://%s:%d%s\n", BACKEND_HOST, BACKEND_PORT, wsUrl.c_str());
    webSocket.begin(BACKEND_HOST, BACKEND_PORT, wsUrl.c_str());
    webSocket.onEvent(webSocketEvent);
    webSocket.setReconnectInterval(2000);
    webSocket.enableHeartbeat(15000, 3000, 2);

    lastPacketReceivedTime = millis();
    Serial.println("[ESP8266] Alert Unit Ready.");
}

// ==============================================================================
// 3.6 MAIN SUPERLOOP
// ==============================================================================
void loop() {
    webSocket.loop();
    checkWiFiConnection();
    updateStatusLed();

    unsigned long now = millis();

    // 1. 30 FPS Butter-Smooth RGB Interpolation & Animation Render
    if (now - lastAnimUpdate >= 33) {
        lastAnimUpdate = now;
        updateRgbAnimation();
    }

    // 2. Non-blocking Buzzer Rhythm
    updateBuzzerPattern();

    // 3. Periodic Telemetry Heartbeat
    if (now - lastHeartbeatTime >= HEARTBEAT_INTERVAL_MS) {
        lastHeartbeatTime = now;
        sendHeartbeat();
    }

    // 4. Offline Fallback
    if (isWsConnected && (now - lastPacketReceivedTime > OFFLINE_TIMEOUT_MS)) {
        if (currentPriority > 1) {
            setSystemState(3, "BACKEND OFFLINE", "ORANGE_BREATH", 255, 90, 0, "OFF");
        }
    }
}

void updateStatusLed() {
    unsigned long now = millis();
    if (!isWsConnected) {
        if (now - lastStatusLedToggle >= 200) {
            lastStatusLedToggle = now;
            digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN));
        }
    } else {
        digitalWrite(STATUS_LED_PIN, LOW); // Solid ON when connected
    }
}

// ==============================================================================
// 3.7 SYSTEM STATE MANAGER
// ==============================================================================
void setSystemState(int priority, const String& label, const String& rgbMode, uint8_t r, uint8_t g, uint8_t b, const String& buzzer, bool isAcknowledge) {
    bool isReset = isAcknowledge || (label.indexOf("Ready") >= 0) || (label.indexOf("Reset") >= 0) || (label.indexOf("Monitoring") >= 0) || (priority == 4 && rgbMode == "WHITE_BREATH");

    // If active state is SOS (priority 0), ONLY an explicit reset/acknowledge packet can unlock it!
    if (currentPriority == 0 && priority != 0 && !isReset) {
        Serial.printf("[SOS LOCKED] Ignoring lower-priority command '%s' (Priority %d)\n", label.c_str(), priority);
        return;
    }

    currentPriority = priority;
    currentDisplayLabel = label;
    currentRgbMode = rgbMode;
    currentBuzzerPattern = buzzer;

    targetR = (float)r;
    targetG = (float)g;
    targetB = (float)b;

    // Immediately silence buzzer on reset or normal state
    if (isReset || priority == 4 || buzzer == "OFF") {
        buzzerState = false;
        setBuzzerSound(false);
    }

    // Dynamically scale brightness targets based on situational urgency
    if (priority == 0)       targetBrightness = 255.0f; // SOS: 100% full punch
    else if (priority == 1)  targetBrightness = 230.0f; // Critical: High punch
    else if (priority == 2)  targetBrightness = 175.0f; // Warning: Noticeable
    else if (priority == 3)  targetBrightness = 120.0f; // Info: Gentle
    else                     targetBrightness = 90.0f;  // Normal: Ambient White

    Serial.printf("[STATE CHANGE] Priority=%d | Event='%s' | RGB=%s RGB(%d,%d,%d) | Buzzer=%s\n",
                  priority, label.c_str(), rgbMode.c_str(), r, g, b, buzzer.c_str());
}

// ==============================================================================
// 3.8 ADVANCED SMOOTH RGB ANIMATION ENGINE (WS2812 NEOPIXEL RING)
// ==============================================================================
void updateRgbAnimation() {
    // 1. Smooth exponential lerp towards target RGB and brightness
    float lerpSpeed = (currentPriority <= 1) ? 0.26f : 0.14f; // Faster response on emergency alerts
    currentR += (targetR - currentR) * lerpSpeed;
    currentG += (targetG - currentG) * lerpSpeed;
    currentB += (targetB - currentB) * lerpSpeed;
    currentBrightness += (targetBrightness - currentBrightness) * lerpSpeed;

    animPhase += 0.08f;
    if (animPhase > 628.3185f) animPhase -= 628.3185f; // Cycle cleanly (100 * 2PI)

    // 2. Compute dynamic lighting modulation based on active mode
    if (currentRgbMode == "WHITE_BREATH" || currentRgbMode == "AMBIENT_BREATH" || currentRgbMode == "CYAN_BREATH" || currentRgbMode == "BLUE_BREATH" || currentRgbMode == "ORANGE_BREATH") {
        // Smooth sine wave natural breathing for ambient silence or calm states
        float breath = 0.35f + 0.65f * (sin(animPhase * 0.85f) * 0.5f + 0.5f);
        uint8_t r = gammaCorrect(currentR, currentBrightness, breath);
        uint8_t g = gammaCorrect(currentG, currentBrightness, breath);
        uint8_t b = gammaCorrect(currentB, currentBrightness, breath);
        for (int i = 0; i < RGB_PIXEL_COUNT; i++) strip.setPixelColor(i, strip.Color(r, g, b));
    }
    else if (currentRgbMode == "WHITE_SOLID" || currentRgbMode == "GREEN_SOLID") {
        uint8_t r = gammaCorrect(currentR, currentBrightness);
        uint8_t g = gammaCorrect(currentG, currentBrightness);
        uint8_t b = gammaCorrect(currentB, currentBrightness);
        for (int i = 0; i < RGB_PIXEL_COUNT; i++) strip.setPixelColor(i, strip.Color(r, g, b));
    }
    else if (currentRgbMode == "RED_PULSE" || currentRgbMode == "MAGENTA_PULSE" || currentRgbMode == "ORANGE_PULSE") {
        // High-contrast smooth heartbeat pulse (sine squared with sharp crest)
        float pulse = pow(sin(animPhase * 1.8f) * 0.5f + 0.5f, 2.0f);
        float mod = 0.22f + 0.78f * pulse;
        uint8_t r = gammaCorrect(currentR, currentBrightness, mod);
        uint8_t g = gammaCorrect(currentG, currentBrightness, mod);
        uint8_t b = gammaCorrect(currentB, currentBrightness, mod);
        for (int i = 0; i < RGB_PIXEL_COUNT; i++) strip.setPixelColor(i, strip.Color(r, g, b));
    }
    else if (currentRgbMode == "RED_STROBE") {
        // Rapid commanding emergency strobe with smooth decay
        int step = ((int)(animPhase * 3.5f)) % 6;
        float mod = (step == 0 || step == 2) ? 1.0f : 0.05f;
        uint8_t r = gammaCorrect(currentR, currentBrightness, mod);
        uint8_t g = gammaCorrect(currentG, currentBrightness, mod);
        uint8_t b = gammaCorrect(currentB, currentBrightness, mod);
        for (int i = 0; i < RGB_PIXEL_COUNT; i++) strip.setPixelColor(i, strip.Color(r, g, b));
    }
    else if (currentRgbMode == "GLASS_SPARKLE") {
        // Shimmering Ruby Red with dynamic diamond-white sparkles moving across the ring
        float baseMod = 0.35f + 0.25f * (sin(animPhase * 1.2f) * 0.5f + 0.5f);
        uint8_t br = gammaCorrect(currentR, currentBrightness, baseMod);
        uint8_t bg = gammaCorrect(currentG, currentBrightness, baseMod);
        uint8_t bb = gammaCorrect(currentB, currentBrightness, baseMod);
        for (int i = 0; i < RGB_PIXEL_COUNT; i++) strip.setPixelColor(i, strip.Color(br, bg, bb));

        // Sparkle 2 random pixels in bright crystal white
        int sparkle1 = ((int)(animPhase * 4.0f)) % RGB_PIXEL_COUNT;
        int sparkle2 = (sparkle1 + (RGB_PIXEL_COUNT / 2)) % RGB_PIXEL_COUNT;
        strip.setPixelColor(sparkle1, strip.Color(255, 255, 255));
        strip.setPixelColor(sparkle2, strip.Color(255, 240, 240));
    }
    else if (currentRgbMode == "EMERGENCY_STROBE") {
        // High-visibility SOS split-ring alternating Red & White beacon
        int phaseStep = ((int)(animPhase * 4.0f)) % 4;
        bool invertHalf = (phaseStep >= 2);
        for (int i = 0; i < RGB_PIXEL_COUNT; i++) {
            bool firstHalf = (i < (RGB_PIXEL_COUNT / 2));
            if (firstHalf ^ invertHalf) {
                strip.setPixelColor(i, strip.Color(255, 0, 30));   // Blazing Red
            } else {
                strip.setPixelColor(i, strip.Color(255, 255, 255)); // Brilliant White
            }
        }
    }
    else if (currentRgbMode == "YELLOW_PULSE") {
        // Warm double-chime pulse
        float pulse = pow(sin(animPhase * 1.5f) * 0.5f + 0.5f, 1.8f);
        float mod = 0.25f + 0.75f * pulse;
        uint8_t r = gammaCorrect(currentR, currentBrightness, mod);
        uint8_t g = gammaCorrect(currentG, currentBrightness, mod);
        uint8_t b = gammaCorrect(currentB, currentBrightness, mod);
        for (int i = 0; i < RGB_PIXEL_COUNT; i++) strip.setPixelColor(i, strip.Color(r, g, b));
    }
    else if (currentRgbMode == "YELLOW_FLASH") {
        // Sharp impact flash for door knock with smooth fade
        float mod = pow(fmod(animPhase * 1.2f, 1.0f), 2.5f);
        mod = 1.0f - mod; // Peak at 1.0, decay to 0.0
        if (mod < 0.18f) mod = 0.18f;
        uint8_t r = gammaCorrect(currentR, currentBrightness, mod);
        uint8_t g = gammaCorrect(currentG, currentBrightness, mod);
        uint8_t b = gammaCorrect(currentB, currentBrightness, mod);
        for (int i = 0; i < RGB_PIXEL_COUNT; i++) strip.setPixelColor(i, strip.Color(r, g, b));
    }
    else if (currentRgbMode == "CYAN_BREATH" || currentRgbMode == "BLUE_BREATH" || currentRgbMode == "AMBIENT_BREATH" || currentRgbMode == "ORANGE_BREATH") {
        // Smooth sine wave natural breathing
        float breath = 0.30f + 0.70f * (sin(animPhase * 0.85f) * 0.5f + 0.5f);
        uint8_t r = gammaCorrect(currentR, currentBrightness, breath);
        uint8_t g = gammaCorrect(currentG, currentBrightness, breath);
        uint8_t b = gammaCorrect(currentB, currentBrightness, breath);
        for (int i = 0; i < RGB_PIXEL_COUNT; i++) strip.setPixelColor(i, strip.Color(r, g, b));
    }
    else if (currentRgbMode == "PURPLE_GLOW") {
        // Radiant violet soft celestial wave
        float mod = 0.40f + 0.60f * (sin(animPhase * 0.95f) * 0.5f + 0.5f);
        uint8_t r = gammaCorrect(currentR, currentBrightness, mod);
        uint8_t g = gammaCorrect(currentG, currentBrightness, mod);
        uint8_t b = gammaCorrect(currentB, currentBrightness, mod);
        for (int i = 0; i < RGB_PIXEL_COUNT; i++) strip.setPixelColor(i, strip.Color(r, g, b));
    }
    else if (currentRgbMode == "PEACH_SPARKLE") {
        // Warm peach gold with joyful rhythmic shimmer
        float mod = 0.35f + 0.65f * (sin(animPhase * 1.4f) * 0.5f + 0.5f);
        uint8_t r = gammaCorrect(currentR, currentBrightness, mod);
        uint8_t g = gammaCorrect(currentG, currentBrightness, mod);
        uint8_t b = gammaCorrect(currentB, currentBrightness, mod);
        for (int i = 0; i < RGB_PIXEL_COUNT; i++) strip.setPixelColor(i, strip.Color(r, g, b));
    }
    else if (currentRgbMode == "INDIGO_CHASE") {
        // Rotating comet melody around the ring for music
        float headPos = fmod(animPhase * 2.2f, (float)RGB_PIXEL_COUNT);
        for (int i = 0; i < RGB_PIXEL_COUNT; i++) {
            float dist = fabs((float)i - headPos);
            if (dist > (RGB_PIXEL_COUNT / 2.0f)) dist = RGB_PIXEL_COUNT - dist;
            float falloff = 1.0f - (dist / 4.0f);
            if (falloff < 0.15f) falloff = 0.15f;
            uint8_t r = gammaCorrect(currentR, currentBrightness, falloff);
            uint8_t g = gammaCorrect(currentG, currentBrightness, falloff);
            uint8_t b = gammaCorrect(currentB, currentBrightness, falloff);
            strip.setPixelColor(i, strip.Color(r, g, b));
        }
    }
    else {
        // Default solid fallback with smooth gamma
        uint8_t r = gammaCorrect(currentR, currentBrightness);
        uint8_t g = gammaCorrect(currentG, currentBrightness);
        uint8_t b = gammaCorrect(currentB, currentBrightness);
        for (int i = 0; i < RGB_PIXEL_COUNT; i++) strip.setPixelColor(i, strip.Color(r, g, b));
    }

    strip.show();
}

// ==============================================================================
// 3.9 ACOUSTIC BUZZER RHYTHMS
// ==============================================================================
void updateBuzzerPattern() {
    unsigned long now = millis();

    if (currentBuzzerPattern == "OFF") {
        if (buzzerState) {
            buzzerState = false;
            setBuzzerSound(false);
        }
        return;
    }

    if (currentBuzzerPattern == "MODERATE_BEEP" || currentBuzzerPattern == "SHORT_BEEP") {
        // Wise acoustic feedback for moderate events: polite, gentle 80ms tone every 2500ms
        unsigned long cycle = now % 2500;
        bool shouldBeOn = (cycle < 80);
        if (buzzerState != shouldBeOn) {
            buzzerState = shouldBeOn;
            setBuzzerSound(buzzerState, 2000);
        }
    }
    else if (currentBuzzerPattern == "CRITICAL_ALARM" || currentBuzzerPattern == "ALARM_BURST") {
        // High-urgency alert burst for life safety emergencies: 180ms on, 180ms off
        unsigned long cycle = now % 360;
        bool shouldBeOn = (cycle < 180);
        if (buzzerState != shouldBeOn) {
            buzzerState = shouldBeOn;
            setBuzzerSound(buzzerState, 2800);
        }
    }
    else if (currentBuzzerPattern == "SOS_ALARM") {
        // High-pitch dual-tone alternating siren
        unsigned long cycle = now % 240;
        int freq = (cycle < 120) ? 3200 : 2400;
        setBuzzerSound(true, freq);
    }
}

// ==============================================================================
// 3.10 WEBSOCKET EVENT DISPATCHER
// ==============================================================================
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    switch (type) {
        case WStype_DISCONNECTED:
            isWsConnected = false;
            Serial.println("[WS] Disconnected from Backend.");
            if (currentPriority > 1) {
                setSystemState(3, "Reconnecting...", "ORANGE_BREATH", 255, 90, 0, "OFF");
            }
            break;

        case WStype_CONNECTED:
            isWsConnected = true;
            lastPacketReceivedTime = millis();
            Serial.println("✅ [WS] Connected to EchoSense Portal!");
            setSystemState(4, "System Ready", "WHITE_BREATH", 255, 255, 255, "OFF", true);
            
            // Connection chirp
            setBuzzerSound(true, 2800);
            delay(80);
            setBuzzerSound(false);
            delay(60);
            setBuzzerSound(true, 3500);
            delay(100);
            setBuzzerSound(false);

            sendHeartbeat();
            break;

        case WStype_TEXT: {
            lastPacketReceivedTime = millis();
            JsonDocument doc;
            DeserializationError err = deserializeJson(doc, payload, length);
            if (err) return;

            const char* msgType = doc["type"] | "";
            if (strcmp(msgType, "SET_STATE") == 0) {
                int priority = doc["priority"] | 4;
                const char* label = doc["displayLabel"] | "Alert";
                const char* rgbMode = doc["rgbMode"] | "WHITE_BREATH";
                const char* buzzer = doc["buzzerPattern"] | "OFF";
                bool isAcknowledge = doc["isAcknowledge"] | false;

                JsonArray rgbArr = doc["rgbColor"];
                uint8_t r = rgbArr[0] | 255;
                uint8_t g = rgbArr[1] | 255;
                uint8_t b = rgbArr[2] | 255;

                setSystemState(priority, label, rgbMode, r, g, b, buzzer, isAcknowledge);
            }
            else if (strcmp(msgType, "ACKNOWLEDGE") == 0 || strcmp(msgType, "RESET_STATE") == 0) {
                Serial.println("[WS] Explicit ACKNOWLEDGE received. Clearing all alerts to White Ambient.");
                setSystemState(4, "System Ready", "WHITE_BREATH", 255, 255, 255, "OFF", true);
            }
            break;
        }

        default:
            break;
    }
}

void sendHeartbeat() {
    if (!isWsConnected) return;

    JsonDocument doc;
    doc["type"] = "HEARTBEAT";
    doc["deviceId"] = ESP8266_DEVICE_ID;
    doc["rssi"] = WiFi.RSSI();
    doc["uptime"] = millis() / 1000;
    doc["firmwareVersion"] = "1.2.0";
    doc["actuators"]["rgbRing"] = "ACTIVE";
    doc["actuators"]["buzzer"] = "READY";
    doc["status"] = "ONLINE";

    String jsonString;
    serializeJson(doc, jsonString);
    webSocket.sendTXT(jsonString);
}

void setupWiFi() {
    Serial.printf("[WiFi] Connecting to %s ", WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 35) {
        delay(250);
        Serial.print(".");

        // Rotating yellow chase animation while connecting
        int ledIdx = attempts % RGB_PIXEL_COUNT;
        strip.clear();
        strip.setPixelColor(ledIdx, strip.Color(255, 180, 0));
        strip.setPixelColor((ledIdx + 1) % RGB_PIXEL_COUNT, strip.Color(180, 80, 0));
        strip.show();

        digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN));
        attempts++;
    }
    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\n✅ [WiFi] Connected! IP: %s (RSSI: %d dBm)\n",
                      WiFi.localIP().toString().c_str(), WiFi.RSSI());
        for (int i = 0; i < RGB_PIXEL_COUNT; i++) strip.setPixelColor(i, strip.Color(0, 255, 60));
        strip.show();
        digitalWrite(STATUS_LED_PIN, LOW);
    } else {
        Serial.println("\n⚠️ [WiFi] Connection timeout. Retrying in background.");
        for (int i = 0; i < RGB_PIXEL_COUNT; i++) strip.setPixelColor(i, strip.Color(255, 100, 0));
        strip.show();
    }
}

void checkWiFiConnection() {
    unsigned long now = millis();
    if (now - lastWifiCheckTime >= 6000) {
        lastWifiCheckTime = now;
        if (WiFi.status() != WL_CONNECTED) {
            WiFi.reconnect();
        }
    }
}

#endif // ESP8266
