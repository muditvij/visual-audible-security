/**
 * ==============================================================================
 * EchoSense ESP8266 Alert Unit Firmware (PlatformIO & Arduino C++)
 * ==============================================================================
 * ULTRA-RELIABLE SENSORY ALERT UNIT (100% STANDALONE - NO LINKED FILES)
 * 
 * Hardware Connections (Standard Conflict-Free Pins):
 * - Buzzer Module Signal (IP/SIG/S) -> NodeMCU D1 (GPIO 5)
 * - Buzzer Module VCC               -> NodeMCU 3V3 (or VIN)
 * - Buzzer Module GND               -> NodeMCU GND
 * - WS2812 RGB Ring Data In (DI)   -> NodeMCU D2 (GPIO 4)
 * - WS2812 RGB Ring Power (5V/VDD)  -> NodeMCU VIN (5V USB power - NEVER 3.3V!)
 * - WS2812 RGB Ring Ground (GND)    -> NodeMCU GND
 * - Built-in Status LED             -> NodeMCU D4 (GPIO 2)
 */

#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include <Adafruit_NeoPixel.h>

// ==============================================================================
// 1. CONFIGURATION (EDIT YOUR WI-FI CREDENTIALS & LAPTOP IP HERE)
// ==============================================================================
#define WIFI_SSID           "VijHouse-JioFiber-4G"
#define WIFI_PASSWORD       "mudit@9152787816"

#define BACKEND_HOST        "192.168.29.19"   // Laptop IPv4 address running EchoSense
#define BACKEND_PORT        8000

#define ESP8266_DEVICE_ID   "ESP8266_ALERT_01"
#define ESP8266_API_KEY     "esp8266_auth_token_38c92a17df40c"

// Standard Safe Pins (Zero Boot Conflicts)
#define BUZZER_PIN          5   // NodeMCU D1 (GPIO 5)
#define BUZZER_ACTIVE_LOW   false // Set true if your 3-pin buzzer module is Active-LOW
#define RGB_RING_PIN        4   // NodeMCU D2 (GPIO 4)
#define RGB_PIXEL_COUNT     16  // Number of LEDs in your WS2812 NeoPixel ring
#define STATUS_LED_PIN      2   // NodeMCU D4 (GPIO 2 - Onboard Blue LED)

#define HEARTBEAT_INTERVAL_MS 5000
#define OFFLINE_TIMEOUT_MS    15000

// ==============================================================================
// 2. HARDWARE DRIVERS & SMOOTH TRANSITION STATE
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
String currentRgbMode = "GREEN_SOLID";
String currentBuzzerPattern = "OFF";

// High-Precision Smooth Color Lerp & Transition Engine
float currentR = 0.0f, currentG = 255.0f, currentB = 80.0f; // Smoothed rendered color
float targetR  = 0.0f, targetG  = 255.0f, targetB  = 80.0f; // Target color from AI Hub
float currentBrightness = 110.0f;
float targetBrightness  = 110.0f;
float animPhase = 0.0f;

bool buzzerState = false;

// Function Prototypes
void setupHardwareTest();
void setupWiFi();
void checkWiFiConnection();
void setSystemState(int priority, const String& label, const String& rgbMode, uint8_t r, uint8_t g, uint8_t b, const String& buzzer);
void updateRgbAnimation();
void updateBuzzerPattern();
void setBuzzerSound(bool on, int freq = 2400);
void updateStatusLed();
void sendHeartbeat();
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length);
uint8_t gammaCorrect(float val, float brightness, float mod = 1.0f);

// ==============================================================================
// 3. SOUND DRIVER (SUPPORTS BOTH ACTIVE & PASSIVE BUZZERS + ACTIVE-LOW MODULES)
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
// 4. PERCEPTUAL GAMMA CORRECTION HELPER
// ==============================================================================
uint8_t gammaCorrect(float val, float brightness, float mod) {
    float norm = (val / 255.0f) * (brightness / 255.0f) * mod;
    if (norm <= 0.001f) return 0;
    if (norm >= 1.0f) return 255;
    // Perceptual quadratic gamma curve prevents harsh color-stepping
    return (uint8_t)(norm * norm * 255.0f + 0.5f);
}

// ==============================================================================
// 5. HARDWARE SELF-TEST (SMOOTH COLOR VERIFICATION SWEEP)
// ==============================================================================
void setupHardwareTest() {
    Serial.println("\n[HARDWARE TEST] Running smooth NeoPixel color verification sweep...");
    strip.begin();
    strip.setBrightness(140);

    // Smooth test sweep through primary alert spectrum
    uint32_t testColors[] = {
        strip.Color(255, 10, 10),   // Critical Red
        strip.Color(255, 180, 0),   // Warning Amber
        strip.Color(0, 220, 255),   // Domestic Cyan
        strip.Color(175, 55, 255),  // Info Violet
        strip.Color(0, 255, 80)     // Normal Emerald Green
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
// 6. SETUP ENTRY POINT
// ==============================================================================
void setup() {
    Serial.begin(115200);
    delay(300);

    Serial.println("\n=================================================");
    Serial.println("   ECHOSENSE ESP8266 ALERT UNIT (STANDALONE)    ");
    Serial.println("   Buzzer Pin: NodeMCU D1 (GPIO 5)              ");
    Serial.println("   RGB Ring Pin: NodeMCU D2 (GPIO 4)            ");
    Serial.println("   Status LED:   NodeMCU D4 (GPIO 2)            ");
    Serial.println("   Smooth Transition & Full-Spectrum Lighting    ");
    Serial.println("=================================================");

    pinMode(STATUS_LED_PIN, OUTPUT);
    digitalWrite(STATUS_LED_PIN, HIGH); // Built-in LED OFF (Active-LOW)

    pinMode(BUZZER_PIN, OUTPUT);
    setBuzzerSound(false);

    // Run instant power-on test
    setupHardwareTest();

    setSystemState(4, "Connecting Wi-Fi...", "YELLOW_PULSE", 255, 180, 0, "OFF");

    setupWiFi();

    // Initialize WebSocket connection to EchoSense Laptop Portal
    String wsUrl = "/ws/esp8266?token=" + String(ESP8266_API_KEY);
    Serial.printf("[WS] Connecting to ws://%s:%d%s\n", BACKEND_HOST, BACKEND_PORT, wsUrl.c_str());
    webSocket.begin(BACKEND_HOST, BACKEND_PORT, wsUrl.c_str());
    webSocket.onEvent(webSocketEvent);
    webSocket.setReconnectInterval(2000);
    webSocket.enableHeartbeat(15000, 3000, 2);

    lastPacketReceivedTime = millis();
    Serial.println("[ESP8266] Alert Unit fully initialized and running.");
}

// ==============================================================================
// 7. MAIN SUPERLOOP
// ==============================================================================
void loop() {
    webSocket.loop();
    checkWiFiConnection();
    updateStatusLed();

    unsigned long now = millis();

    // 1. 30 FPS Smooth RGB Animation Render Frame
    if (now - lastAnimUpdate >= 33) {
        lastAnimUpdate = now;
        updateRgbAnimation();
    }

    // 2. Non-blocking Buzzer Alert Rhythm
    updateBuzzerPattern();

    // 3. Periodic Health Telemetry Heartbeat
    if (now - lastHeartbeatTime >= HEARTBEAT_INTERVAL_MS) {
        lastHeartbeatTime = now;
        sendHeartbeat();
    }

    // 4. Offline Fallback Warning
    if (isWsConnected && (now - lastPacketReceivedTime > OFFLINE_TIMEOUT_MS)) {
        if (currentPriority > 1) {
            setSystemState(3, "BACKEND OFFLINE", "ORANGE_BREATH", 255, 90, 0, "OFF");
        }
    }
}

// ==============================================================================
// 8. STATUS LED INDICATOR
// ==============================================================================
void updateStatusLed() {
    unsigned long now = millis();
    if (!isWsConnected) {
        // Fast blinking indicates attempting to connect
        if (now - lastStatusLedToggle >= 200) {
            lastStatusLedToggle = now;
            digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN));
        }
    } else {
        // Solid ON when connected (Active-LOW = LOW is ON)
        digitalWrite(STATUS_LED_PIN, LOW);
    }
}

// ==============================================================================
// 9. STATE MANAGER
// ==============================================================================
void setSystemState(int priority, const String& label, const String& rgbMode, uint8_t r, uint8_t g, uint8_t b, const String& buzzer) {
    // If active emergency SOS is engaged, ignore lower priority cues
    if (currentPriority == 0 && priority != 0) return;

    currentPriority = priority;
    currentDisplayLabel = label;
    currentRgbMode = rgbMode;
    currentBuzzerPattern = buzzer;

    targetR = (float)r;
    targetG = (float)g;
    targetB = (float)b;

    // Dynamically scale brightness targets based on situational urgency
    if (priority == 0)       targetBrightness = 255.0f; // SOS: 100% full punch
    else if (priority == 1)  targetBrightness = 230.0f; // Critical: High punch
    else if (priority == 2)  targetBrightness = 175.0f; // Warning: Noticeable
    else if (priority == 3)  targetBrightness = 120.0f; // Info: Gentle
    else                     targetBrightness = 75.0f;  // Normal: Ambient

    Serial.printf("[STATE CHANGE] Priority=%d | Event='%s' | RGB=%s RGB(%d,%d,%d) | Buzzer=%s\n",
                  priority, label.c_str(), rgbMode.c_str(), r, g, b, buzzer.c_str());
}

// ==============================================================================
// 10. RGB LIGHTING ANIMATIONS (WS2812 NEOPIXEL RING)
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
    if (currentRgbMode == "GREEN_SOLID") {
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
// 11. ACOUSTIC BUZZER RHYTHMS
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

    if (currentBuzzerPattern == "SHORT_BEEP") {
        unsigned long cycle = now % 2000;
        bool shouldBeOn = (cycle < 120);
        if (buzzerState != shouldBeOn) {
            buzzerState = shouldBeOn;
            setBuzzerSound(buzzerState, 2200);
        }
    }
    else if (currentBuzzerPattern == "ALARM_BURST") {
        unsigned long cycle = now % 400;
        bool shouldBeOn = (cycle < 220);
        if (buzzerState != shouldBeOn) {
            buzzerState = shouldBeOn;
            setBuzzerSound(buzzerState, 2600);
        }
    }
    else if (currentBuzzerPattern == "SOS_ALARM") {
        unsigned long cycle = now % 180;
        bool shouldBeOn = (cycle < 100);
        if (buzzerState != shouldBeOn) {
            buzzerState = shouldBeOn;
            setBuzzerSound(buzzerState, 3000);
        }
    }
}

// ==============================================================================
// 12. WEBSOCKET EVENT DISPATCHER
// ==============================================================================
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
    switch (type) {
        case WStype_DISCONNECTED:
            isWsConnected = false;
            Serial.println("[WS] Disconnected from EchoSense Portal.");
            if (currentPriority > 1) {
                setSystemState(3, "Reconnecting...", "ORANGE_BREATH", 255, 90, 0, "OFF");
            }
            break;

        case WStype_CONNECTED:
            isWsConnected = true;
            lastPacketReceivedTime = millis();
            Serial.println("✅ [WS] Connected to EchoSense Hub!");
            setSystemState(4, "System Ready", "GREEN_SOLID", 0, 255, 80, "OFF");
            
            // Connected chime
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
            if (err) {
                Serial.printf("[JSON ERROR] Deserialization failed: %s\n", err.c_str());
                return;
            }

            const char* msgType = doc["type"] | "";
            if (strcmp(msgType, "SET_STATE") == 0) {
                int priority = doc["priority"] | 4;
                const char* label = doc["displayLabel"] | "Alert";
                const char* rgbMode = doc["rgbMode"] | "GREEN_SOLID";
                const char* buzzer = doc["buzzerPattern"] | "OFF";

                JsonArray rgbArr = doc["rgbColor"];
                uint8_t r = rgbArr[0] | 0;
                uint8_t g = rgbArr[1] | 255;
                uint8_t b = rgbArr[2] | 80;

                setSystemState(priority, label, rgbMode, r, g, b, buzzer);
            }
            break;
        }

        default:
            break;
    }
}

        default:
            break;
    }
}

// ==============================================================================
// 12. TELEMETRY TRANSMITTER
// ==============================================================================
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

// ==============================================================================
// 13. WI-FI MANAGER WITH VISUAL CONNECTION FEEDBACK
// ==============================================================================
void setupWiFi() {
    Serial.printf("[WiFi] Connecting to %s ", WIFI_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 35) {
        delay(250);
        Serial.print(".");

        // Rotating Yellow chase animation while connecting!
        int ledIdx = attempts % RGB_PIXEL_COUNT;
        strip.clear();
        strip.setPixelColor(ledIdx, strip.Color(255, 180, 0));
        strip.setPixelColor((ledIdx + 1) % RGB_PIXEL_COUNT, strip.Color(180, 80, 0));
        strip.show();

        digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN));
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("\n✅ [WiFi] Connected! IP Address: %s (RSSI: %d dBm)\n",
                      WiFi.localIP().toString().c_str(), WiFi.RSSI());
        // Green flash to confirm Wi-Fi
        for (int i = 0; i < RGB_PIXEL_COUNT; i++) strip.setPixelColor(i, strip.Color(0, 255, 60));
        strip.show();
        digitalWrite(STATUS_LED_PIN, LOW); // Solid ON
    } else {
        Serial.println("\n⚠️ [WiFi] Timeout. Retrying in background...");
        // Orange breathing to indicate waiting for connection
        for (int i = 0; i < RGB_PIXEL_COUNT; i++) strip.setPixelColor(i, strip.Color(255, 100, 0));
        strip.show();
    }
}

void checkWiFiConnection() {
    unsigned long now = millis();
    if (now - lastWifiCheckTime >= 6000) {
        lastWifiCheckTime = now;
        if (WiFi.status() != WL_CONNECTED) {
            Serial.println("[WiFi] Lost connection. Reconnecting...");
            WiFi.reconnect();
        }
    }
}
