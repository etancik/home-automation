/*
 * ESP32 CO2 Sensor with Home Assistant Integration
 * Hardware: LaskaKit ESPlan ESP32 + SCD41 CO2 sensor
 * 
 * CRITICAL RESOURCES:
 * - LaskaKit ESPlan pinout: https://github.com/LaskaKit/ESPlan/
 * - SCD41 datasheet: https://sensirion.com/products/catalog/SCD41/
 * - Home Assistant MQTT Discovery: https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery
 * - PubSubClient buffer limit fix: https://github.com/knolleary/pubsubclient
 * 
 * SECURITY: wifi_config.h contains credentials and is gitignored
 */

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <SensirionI2CScd4x.h>
#include <WiFi.h>
#define MQTT_MAX_PACKET_SIZE 1024
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include "../wifi_config.h"

// ESPlan board-specific pins (CRITICAL: different from standard ESP32)
#define SDA_PIN 33      // ESPlan I2C SDA (not GPIO21)
#define SCL_PIN 32      // ESPlan I2C SCL (not GPIO22)  
#define POWER_PIN 2     // μŠup connector power control

// OLED display configuration
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define SCREEN_ADDRESS 0x3C

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
SensirionI2CScd4x scd4x;
WiFiClient espClient;
PubSubClient mqtt(espClient);

// Global variables
unsigned long lastMqttPublish = 0;
const unsigned long mqttPublishInterval = 30000; // 30 seconds
bool wifiConnected = false;
bool mqttConnected = false;
unsigned long lastDiscoveryPublish = 0;
bool forceDiscovery = false;

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

void setup() {
    Serial.begin(115200);
    Serial.println("ESPlan CO2 Sensor");
    
    // CRITICAL: Power up μŠup connectors
    pinMode(POWER_PIN, OUTPUT);
    digitalWrite(POWER_PIN, HIGH);
    delay(100);
    
    // Initialize I2C with ESPlan-specific pins
    Wire.begin(SDA_PIN, SCL_PIN);
    
    // Initialize OLED
    if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
        Serial.println("OLED initialization failed");
        return;
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
    unsigned long discoveryInterval = (millis() < 600000) ? 60000 : 300000;
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
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    
    // Header
    display.setTextSize(1);
    display.setCursor(0, 0);
    display.println("LIVING ROOM");
    
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
    
    String clientId = "esplan_co2_sensor";
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

void publishHomeAssistantDiscovery() {
    if (!mqttConnected) return;
    
    StaticJsonDocument<1536> doc;
    String payload;
    
    // CRITICAL: Device information enables Home Assistant device grouping
    // All sensors with same "identifiers" appear as single device
    JsonObject device = doc.createNestedObject("device");
    device["identifiers"] = "esplan_co2_sensor";
    device["name"] = "ESPlan CO2 Sensor";
    device["model"] = "ESP32 + SCD41";
    device["manufacturer"] = "LaskaKit";
    device["sw_version"] = "1.0";
    
    // CO2 sensor discovery
    doc["state_topic"] = "esplan_co2/state";
    doc["value_template"] = "{{ value_json.co2 }}";
    doc["unique_id"] = "esplan_co2";
    doc["name"] = "CO2";
    doc["unit_of_measurement"] = "ppm";
    doc["device_class"] = "carbon_dioxide";
    doc["state_class"] = "measurement";
    
    serializeJson(doc, payload);
    mqtt.publish("homeassistant/sensor/esplan_co2/co2/config", payload.c_str());
    delay(100);
    
    // Temperature sensor discovery
    doc.clear();
    device = doc.createNestedObject("device");
    device["identifiers"] = "esplan_co2_sensor";
    device["name"] = "ESPlan CO2 Sensor";
    device["model"] = "ESP32 + SCD41";
    device["manufacturer"] = "LaskaKit";
    device["sw_version"] = "1.0";
    
    doc["state_topic"] = "esplan_co2/state";
    doc["value_template"] = "{{ value_json.temperature }}";
    doc["unique_id"] = "esplan_temperature";
    doc["name"] = "Temperature";
    doc["unit_of_measurement"] = "°C";
    doc["device_class"] = "temperature";
    doc["state_class"] = "measurement";
    
    payload = "";
    serializeJson(doc, payload);
    mqtt.publish("homeassistant/sensor/esplan_co2/temperature/config", payload.c_str());
    delay(100);
    
    // Humidity sensor discovery
    doc.clear();
    device = doc.createNestedObject("device");
    device["identifiers"] = "esplan_co2_sensor";
    device["name"] = "ESPlan CO2 Sensor";
    device["model"] = "ESP32 + SCD41";
    device["manufacturer"] = "LaskaKit";
    device["sw_version"] = "1.0";
    
    doc["state_topic"] = "esplan_co2/state";
    doc["value_template"] = "{{ value_json.humidity }}";
    doc["unique_id"] = "esplan_humidity";
    doc["name"] = "Humidity";
    doc["unit_of_measurement"] = "%";
    doc["device_class"] = "humidity";
    doc["state_class"] = "measurement";
    
    payload = "";
    serializeJson(doc, payload);
    mqtt.publish("homeassistant/sensor/esplan_co2/humidity/config", payload.c_str());
    
    Serial.println("Published Home Assistant discovery messages");
}

void publishSensorData(uint16_t co2, float temp, float humidity) {
    if (!mqttConnected || (millis() - lastMqttPublish < mqttPublishInterval)) return;
    
    StaticJsonDocument<200> doc;
    doc["co2"] = co2;
    doc["temperature"] = temp;
    doc["humidity"] = humidity;
    doc["timestamp"] = millis();
    
    String payload;
    serializeJson(doc, payload);
    
    if (mqtt.publish("esplan_co2/state", payload.c_str())) {
        lastMqttPublish = millis();
        Serial.printf("✓ MQTT: CO2=%d, T=%.1f, H=%.1f\n", co2, temp, humidity);
    }
}