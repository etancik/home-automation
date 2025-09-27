#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ESPlan board-specific pins (CRITICAL: different from standard ESP32)
#define SDA_PIN 33      // ESPlan I2C SDA (not GPIO21)
#define SCL_PIN 32      // ESPlan I2C SCL (not GPIO22)  
#define POWER_PIN 2     // μŠup connector power control

// OLED display configuration
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define SCREEN_ADDRESS 0x3C

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

void setup() {
    Serial.begin(115200);
    Serial.println("ESPlan OLED Test");
    
    // CRITICAL: Power up μŠup connectors
    pinMode(POWER_PIN, OUTPUT);
    digitalWrite(POWER_PIN, HIGH);
    delay(100);
    
    // Initialize I2C with ESPlan-specific pins
    Wire.begin(SDA_PIN, SCL_PIN);
    
    // Initialize OLED
    if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
        Serial.println("OLED failed");
        return;
    }
    
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    display.setTextSize(2);
    display.setCursor(0, 0);
    display.println("Hello!");
    display.setTextSize(1);
    display.setCursor(0, 20);
    display.println("ESPlan Working");
    display.display();
    
    Serial.println("OLED initialized successfully");
}

void loop() {
    delay(1000);
}