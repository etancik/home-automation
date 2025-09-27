# ESPlan Development Notes

## Critical Discovery: Non-Standard I2C Pins

**Problem**: Standard ESP32 I2C pins (GPIO21/22) do not work on LaskaKit ESPlan boards.

**Solution**: ESPlan uses different pins:
```cpp
#define SDA_PIN 33      // NOT GPIO21
#define SCL_PIN 32      // NOT GPIO22  
#define POWER_PIN 2     // μŠup connector power
```

## Required Power Control

The μŠup connector requires GPIO2 to be HIGH for sensors to receive power:
```cpp
pinMode(POWER_PIN, OUTPUT);
digitalWrite(POWER_PIN, HIGH);
delay(100);  // Allow stabilization
```

## Hardware Configuration

- **ESPlan Board**: ESP32 with PoE + LAN8720A ethernet
- **OLED Display**: SSD1306 128x64 at I2C address 0x3C
- **Connection**: μŠup connector system (JST-SH 1mm pitch)

## Confirmed Working Setup

This minimal configuration successfully displays "Hello!" on OLED:

```cpp
Wire.begin(33, 32);  // ESPlan-specific pins
display.begin(SSD1306_SWITCHCAPVCC, 0x3C);
```

## Development Environment

- **PlatformIO**: ESP32 framework
- **Libraries**: Adafruit SSD1306, Adafruit GFX
- **Upload**: USB serial connection

## Next Steps for CO2 Integration

Add SCD41 sensor support:
1. Include Sensirion I2C SCD4x library  
2. Initialize sensor at I2C address 0x62
3. Implement periodic measurement reading

The current code provides a working foundation with OLED display confirmed functional.

## Critical Reference Links - DO NOT LOSE

⚠️ **IMPORTANT**: These GitHub repositories contain essential configuration examples and pin mappings that were crucial for the breakthrough. Keep these links for future troubleshooting and expansion:

### LaskaKit Official Repositories
- **ESPlan Examples**: https://github.com/LaskaKit/ESPlan-ESP32-LAN8720A
  - Contains working ESPHome configurations with correct pin mappings
  - Network setup examples for LAN8720A ethernet
  - Power management and RS485 examples for HVAC integration

- **SCD41 CO2 Sensor Examples**: https://github.com/LaskaKit/SCD41-CO2-Sensor  
  - Library integration examples with SparkFun and Sensirion libraries
  - Power control patterns for different ESP32 boards
  - Calibration and measurement interval configurations

- **OLED Display Integration**: https://github.com/LaskaKit/OLED-displej-SSD1306
  - Display layout examples and font configurations
  - I2C address confirmation and troubleshooting
  - Power saving and display management techniques

### Pin Configuration Sources
The critical pin discovery (GPIO33/32 instead of GPIO21/22) came from:
- ESPHome configuration files in ESPlan repository
- μŠup connector wiring documentation on LaskaKit blog
- Hardware schematic references in product documentation

### Why These Links Are Essential
1. **Future Troubleshooting**: If hardware fails or configurations break
2. **Feature Expansion**: RS485 HVAC integration patterns already documented
3. **Library Updates**: When dependencies change, reference implementations help
4. **Hardware Variants**: Different ESPlan revisions may have pin differences
5. **Community Support**: Active issues and discussions for problem solving