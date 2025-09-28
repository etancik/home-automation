/*
 * ESP32 CO2 Sensor with Home Assistant Integration - SCALABLE VERSION
 * Hardware: ESP32 + SCD41 CO2 sensor with OLED display
 * 
 * DEPLOYMENT FOR MULTIPLE DEVICES:
 * 1. Copy device_config.h for each device deployment
 * 2. Update DEVICE_ID, DEVICE_NAME, and DEVICE_LOCATION in device_config.h
 * 3. Examples:
 *    - Living Room: DEVICE_ID="living_room_co2", DEVICE_NAME="Living Room CO2 Sensor"
 *    - Bedroom: DEVICE_ID="bedroom_co2", DEVICE_NAME="Bedroom CO2 Sensor"
 *    - Office: DEVICE_ID="office_co2", DEVICE_NAME="Office CO2 Sensor"
 * 4. Each device appears as separate device in Home Assistant with automatic grouping
 * 5. MQTT topics are automatically namespaced (e.g., living_room_co2/state)
 * 
 * FEATURES:
 * - Automatic Home Assistant MQTT discovery with device grouping
 * - Resilient operation (continues without display if disconnected)
 * - Configurable publishing intervals and discovery refresh
 * - Proper sensor history tracking with state_class: measurement
 * - Legacy discovery message cleanup for smooth upgrades
 * 
 * RESOURCES:
 * - SCD41 datasheet: https://sensirion.com/products/catalog/SCD41/
 * - Home Assistant MQTT Discovery: https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery
 * - PubSubClient buffer configuration: https://github.com/knolleary/pubsubclient
 * 
 * CONFIGURATION: All settings are in device_config.h (gitignored for security)
 */

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <SensirionI2CScd4x.h>
#include <WiFi.h>
#define MQTT_MAX_PACKET_SIZE 1024
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "device_config.h"

// OLED display configuration
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
SensirionI2CScd4x scd4x;
WiFiClient espClient;
PubSubClient mqtt(espClient);

// Global variables
unsigned long lastMqttPublish = 0;
bool wifiConnected = false;
bool mqttConnected = false;
unsigned long lastDiscoveryPublish = 0;
bool forceDiscovery = false;
bool displayAvailable = false;  // Track if display is working

// Function declarations
void showStartupScreen();
void showWaitingScreen();
void showErrorScreen(uint16_t error);
void updateCO2Display(uint16_t co2, float temp, float humidity);
void connectWiFi();
void connectMQTT();
void publishHomeAssistantDiscovery();
void publishSensorData(uint16_t co2, float temp, float humidity);
void handleMQTT();
String buildDiscoveryTopic(const char* sensorType);
String buildStateTopic();
void publishSensorDiscovery(const char* sensorType, const char* name, const char* unit, 
                           const char* deviceClass, const char* valueTemplate);

void setup() {
    Serial.begin(115200);
    Serial.printf("ESPlan CO2 Sensor - Device: %s\n", DEVICE_ID);
    
    // Power up sensor connectors
    pinMode(POWER_PIN, OUTPUT);
    digitalWrite(POWER_PIN, HIGH);
    delay(100);
    
    // Initialize I2C with board-specific pins
    Wire.begin(SDA_PIN, SCL_PIN);
    
    // Initialize OLED (optional - device works without display)
    if (display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
        displayAvailable = true;
        Serial.println("OLED display initialized");
    } else {
        displayAvailable = false;
        Serial.println("OLED display not available - continuing without display");
    }
    
    // Initialize SCD41 sensor
    scd4x.begin(Wire);
    scd4x.stopPeriodicMeasurement();
    delay(500);
    
    // Enable automatic self-calibration
    scd4x.setAutomaticSelfCalibration(true);
    Serial.println("SCD41 auto-calibration enabled");
    
    // Start measurement
    scd4x.startPeriodicMeasurement();
    Serial.println("SCD41 measurement started");
    
    // Initialize WiFi and MQTT
    connectWiFi();
    mqtt.setServer(mqtt_server, mqtt_port);
    mqtt.setBufferSize(1024);  // CRITICAL: Fix PubSubClient 256-byte default limit
    
    showStartupScreen();
}

void loop() {
    static unsigned long lastReading = 0;
    
    handleMQTT();
    
    // Send discovery messages on first connection and periodically
    unsigned long discoveryInterval = (millis() < 600000) ? DISCOVERY_INTERVAL_STARTUP : DISCOVERY_INTERVAL_NORMAL;
    if (mqttConnected && (forceDiscovery || (millis() - lastDiscoveryPublish > discoveryInterval))) {
        publishHomeAssistantDiscovery();
        lastDiscoveryPublish = millis();
        forceDiscovery = false;
    }
    
    // Read sensor every 5+ seconds
    if (millis() - lastReading > 5000) {
        uint16_t co2;
        float temperature, humidity;
        
        uint16_t error = scd4x.readMeasurement(co2, temperature, humidity);
        
        if (error == 0 && co2 != 0) {
            Serial.printf("CO2: %d ppm, T: %.1f°C, H: %.1f%%\n", co2, temperature, humidity);
            updateCO2Display(co2, temperature, humidity);
            publishSensorData(co2, temperature, humidity);
            lastReading = millis();
        } else if (error != 0) {
            showErrorScreen(error);
        } else {
            showWaitingScreen();
        }
    }
    
    delay(1000);
}

void showStartupScreen() {
    if (!displayAvailable) return;
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println("CO2 SENSOR");
    display.setCursor(0, 10);
    display.println("Initializing...");
    display.setCursor(0, 30);
    display.println("ESPlan + SCD41");
    display.setCursor(0, 50);
    display.println("Please wait 5s");
    display.display();
}

void showWaitingScreen() {
    if (!displayAvailable) return;
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println("CO2 SENSOR");
    display.setCursor(0, 20);
    display.println("Warming up...");
    display.setCursor(0, 40);
    display.printf("Uptime: %lus", millis() / 1000);
    display.display();
}

void showErrorScreen(uint16_t error) {
    if (!displayAvailable) return;
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println("SENSOR ERROR");
    display.setCursor(0, 20);
    display.printf("Code: %d", error);
    display.setCursor(0, 40);
    display.println("Check wiring!");
    display.display();
}

void updateCO2Display(uint16_t co2, float temp, float humidity) {
    if (!displayAvailable) return;
    
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    
    // Header
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println(DEVICE_LOCATION);
    
    // Large CO2 reading
    display.setTextSize(3);
    display.setCursor(5, 15);
    display.printf("%d", co2);
    
    display.setTextSize(1);
    display.setCursor(5, 45);
    display.println("ppm CO2");
    
    // Air quality status
    display.setCursor(5, 55);
    if (co2 < 800) display.println("EXCELLENT");
    else if (co2 < 1000) display.println("GOOD");
    else if (co2 < 1400) display.println("MODERATE");
    else display.println("VENTILATE!");
    
    // Temperature & humidity on right side
    display.setCursor(85, 30);
    display.printf("%.1fC", temp);
    display.setCursor(85, 40);
    display.printf("%.0f%%", humidity);
    
    // Connection status (bottom right corner)
    display.setCursor(85, 55);
    if (wifiConnected && mqttConnected) {
        display.println("HA");
    } else if (wifiConnected) {
        display.println("WiFi");
    } else {
        display.println("Local");
    }
    
    display.display();
}



void connectWiFi() {
    if (strlen(wifi_ssid) == 0) {
        Serial.println("WiFi not configured - offline mode");
        return;
    }
    
    Serial.print("Connecting to WiFi");
    WiFi.begin(wifi_ssid, wifi_password);
    
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20) {
        delay(500);
        Serial.print(".");
        attempts++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
        wifiConnected = true;
        Serial.println(" connected!");
        Serial.printf("IP: %s\n", WiFi.localIP().toString().c_str());
    } else {
        Serial.println(" failed - offline mode");
    }
}

void connectMQTT() {
    if (!wifiConnected || mqtt.connected()) return;
    
    Serial.printf("Connecting to MQTT: %s:%d\n", mqtt_server, mqtt_port);
    
    String clientId = String("co2sensor_") + DEVICE_ID;
    bool connected = mqtt.connect(clientId.c_str(), mqtt_user, mqtt_password);
    
    if (connected) {
        Serial.println("MQTT connected!");
        mqttConnected = true;
        forceDiscovery = true;  // Trigger discovery on new connection
    } else {
        Serial.printf("MQTT failed, code: %d\n", mqtt.state());
        mqttConnected = false;
    }
}

void handleMQTT() {
    if (!wifiConnected) return;
    
    if (!mqtt.connected()) {
        mqttConnected = false;
        connectMQTT();
    } else {
        mqttConnected = true;
        mqtt.loop();
    }
}

String buildDiscoveryTopic(const char* sensorType) {
    return String("homeassistant/sensor/") + DEVICE_ID + "/" + sensorType + "/config";
}

String buildStateTopic() {
    return String(DEVICE_ID) + "/state";
}

void publishSensorDiscovery(const char* sensorType, const char* name, const char* unit, 
                           const char* deviceClass, const char* valueTemplate) {
    StaticJsonDocument<1024> doc;
    
    // Device information - consistent across all sensors for grouping
    JsonObject device = doc.createNestedObject("device");
    device["identifiers"] = DEVICE_ID;
    device["name"] = DEVICE_NAME;
    device["model"] = "ESP32 + SCD41";
    device["manufacturer"] = "DIY";
    device["sw_version"] = "2.0";
    
    // Sensor configuration
    doc["state_topic"] = buildStateTopic();
    doc["value_template"] = valueTemplate;
    doc["unique_id"] = String(DEVICE_ID) + "_" + sensorType;
    doc["name"] = name;
    doc["unit_of_measurement"] = unit;
    doc["device_class"] = deviceClass;
    doc["state_class"] = "measurement";
    
    String payload;
    serializeJson(doc, payload);
    
    String topic = buildDiscoveryTopic(sensorType);
    mqtt.publish(topic.c_str(), payload.c_str());
    
    Serial.printf("✓ Discovery: %s -> %s\n", name, topic.c_str());
    delay(100);
}

void publishHomeAssistantDiscovery() {
    if (!mqttConnected) return;
    
    Serial.printf("Publishing discovery for device: %s\n", DEVICE_ID);
    
    // Clean up old discovery messages with previous topic structure
    mqtt.publish("homeassistant/sensor/esplan_co2/co2/config", "");
    mqtt.publish("homeassistant/sensor/esplan_co2/temperature/config", "");  
    mqtt.publish("homeassistant/sensor/esplan_co2/humidity/config", "");
    mqtt.publish("homeassistant/sensor/esplan_co2_sensor/co2/config", "");
    mqtt.publish("homeassistant/sensor/esplan_co2_sensor/temperature/config", "");  
    mqtt.publish("homeassistant/sensor/esplan_co2_sensor/humidity/config", "");
    delay(200);
    
    // Publish discovery messages for each sensor
    publishSensorDiscovery("co2", "CO2", "ppm", "carbon_dioxide", "{{ value_json.co2 }}");
    publishSensorDiscovery("temperature", "Temperature", "°C", "temperature", "{{ value_json.temperature }}");
    publishSensorDiscovery("humidity", "Humidity", "%", "humidity", "{{ value_json.humidity }}");
    
    Serial.println("✓ All discovery messages published");
}

void publishSensorData(uint16_t co2, float temp, float humidity) {
    if (!mqttConnected || (millis() - lastMqttPublish < PUBLISH_INTERVAL)) return;
    
    StaticJsonDocument<200> doc;
    doc["co2"] = co2;
    doc["temperature"] = temp;
    doc["humidity"] = humidity;
    doc["timestamp"] = millis();
    
    String payload;
    serializeJson(doc, payload);
    
    String stateTopic = buildStateTopic();
    if (mqtt.publish(stateTopic.c_str(), payload.c_str())) {
        lastMqttPublish = millis();
        Serial.printf("✓ MQTT [%s]: CO2=%d, T=%.1f, H=%.1f\n", DEVICE_ID, co2, temp, humidity);
    } else {
        Serial.printf("✗ MQTT publish failed to %s\n", stateTopic.c_str());
    }
}