#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <SensirionI2CScd4x.h>

// ESPlan board-specific pins (CRITICAL: different from standard ESP32)
#define SDA_PIN 33      // ESPlan I2C SDA (not GPIO21)
#define SCL_PIN 32      // ESPlan I2C SCL (not GPIO22)  
#define POWER_PIN 2     // μŠup connector power control

// OLED display configuration
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define SCREEN_ADDRESS 0x3C

// I2C addresses
#define SCD41_ADDRESS 0x62  // CO2 sensor address

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
SensirionI2CScd4x scd4x;

// Function declarations
void showStartupScreen();
void showWaitingScreen();
void showErrorScreen(uint16_t error);
void updateCO2Display(uint16_t co2, float temp, float humidity);
void performManualCalibration();

void setup() {
    Serial.begin(115200);
    Serial.println("ESPlan CO2 Sensor Test");
    
    // CRITICAL: Power up μŠup connectors
    pinMode(POWER_PIN, OUTPUT);
    digitalWrite(POWER_PIN, HIGH);
    delay(100);
    
    // Initialize I2C with ESPlan-specific pins
    Wire.begin(SDA_PIN, SCL_PIN);
    
    // Scan I2C devices
    Serial.println("Scanning I2C devices...");
    for (byte addr = 1; addr < 127; addr++) {
        Wire.beginTransmission(addr);
        if (Wire.endTransmission() == 0) {
            Serial.printf("Found I2C device at 0x%02X\n", addr);
        }
    }
    
    // Initialize OLED
    if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
        Serial.println("OLED failed");
        return;
    }
    Serial.println("OLED initialized successfully");
    
    // Initialize SCD41 sensor
    scd4x.begin(Wire);
    
    // Stop potentially running measurement
    uint16_t error = scd4x.stopPeriodicMeasurement();
    if (error) {
        Serial.printf("Error stopping measurement: %d\n", error);
    }
    delay(500);
    
    // Configure sensor calibration
    Serial.println("Configuring SCD41 calibration...");
    
    // Enable automatic self-calibration (ASC)
    // This continuously calibrates the sensor over time (recommended for indoor use)
    error = scd4x.setAutomaticSelfCalibration(true);
    if (error) {
        Serial.printf("Error enabling ASC: %d\n", error);
    } else {
        Serial.println("Automatic Self-Calibration ENABLED");
    }
    
    // Optional: Get sensor info
    uint16_t serial0, serial1, serial2;
    error = scd4x.getSerialNumber(serial0, serial1, serial2);
    if (error == 0) {
        Serial.printf("SCD41 Serial: %04x%04x%04x\n", serial0, serial1, serial2);
    }
    
    // Start periodic measurement
    error = scd4x.startPeriodicMeasurement();
    if (error) {
        Serial.printf("Error starting measurement: %d\n", error);
    } else {
        Serial.println("SCD41 measurement started");
        Serial.println("Note: First readings may take 60+ seconds");
        Serial.println("ASC will calibrate over 7+ days of operation");
    }
    
    // Initial display
    showStartupScreen();
}

void loop() {
    static unsigned long lastReading = 0;
    
    // Read sensor every 5+ seconds (SCD41 requirement)
    if (millis() - lastReading > 5000) {
        uint16_t co2;
        float temperature, humidity;
        
        uint16_t error = scd4x.readMeasurement(co2, temperature, humidity);
        
        if (error == 0 && co2 != 0) {
            // Print to serial
            Serial.printf("CO2: %d ppm, T: %.1f°C, H: %.1f%%\n", 
                         co2, temperature, humidity);
            
            // Update display
            updateCO2Display(co2, temperature, humidity);
            
            lastReading = millis();
        } else if (error != 0) {
            Serial.printf("Sensor read error: %d\n", error);
            showErrorScreen(error);
        } else {
            Serial.println("Waiting for valid measurement...");
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
    
    display.display();
}

void performManualCalibration() {
    // ONLY call this function when the sensor has been exposed to 
    // fresh outdoor air (400-420 ppm) for at least 3 minutes
    Serial.println("=== MANUAL CALIBRATION ===");
    Serial.println("WARNING: Only run this outdoors in fresh air!");
    Serial.println("Sensor should be exposed to ~400ppm CO2 for 3+ minutes");
    
    uint16_t error = scd4x.stopPeriodicMeasurement();
    delay(500);
    
    // Perform forced recalibration to 400 ppm (outdoor reference)
    uint16_t frcCorrection;
    error = scd4x.performForcedRecalibration(400, frcCorrection);
    if (error) {
        Serial.printf("Calibration failed: %d\n", error);
    } else {
        Serial.println("Manual calibration completed!");
        Serial.printf("Sensor calibrated to 400 ppm reference (correction: %d)\n", frcCorrection);
    }
    
    delay(500);
    scd4x.startPeriodicMeasurement();
}