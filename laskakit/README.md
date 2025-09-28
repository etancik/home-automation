# CO2 Sensor - ESP32 Home Assistant Integration

Production-ready CO2 sensor with automatic Home Assistant MQTT discovery. Scalable for multiple rooms.

## Features

- ✅ **Automatic Home Assistant Discovery** - Appears automatically with proper device grouping
- ✅ **Multi-Device Support** - Easy deployment across multiple rooms
- ✅ **OLED Display** - Shows CO2, temperature, humidity, and connection status  
- ✅ **Resilient** - Works without display, handles network disconnections
- ✅ **History Tracking** - Long-term data retention in Home Assistant

## Hardware

- ESP32 board (ESPlan or similar)
- SCD41 CO2 sensor 
- SSD1306 OLED display (128x64, optional)

**Wiring:**
```
ESP32 Pin  →  Component
GPIO 33    →  I2C SDA (SCD41 + OLED)
GPIO 32    →  I2C SCL (SCD41 + OLED)  
3.3V       →  VCC
GND        →  GND
```

## Setup

1. **Configure device:**
   ```bash
   cp src/device_config.template.h src/device_config.h
   ```

2. **Edit `src/device_config.h`:**
   ```cpp
   const char* DEVICE_ID = "living_room_co2";
   const char* DEVICE_NAME = "Living Room CO2 Sensor";
   const char* wifi_ssid = "YourWiFi";
   const char* mqtt_server = "192.168.1.100";
   ```

3. **Install libraries** (PlatformIO):
   - Adafruit GFX Library
   - Adafruit SSD1306
   - Sensirion I2C SCD4x
   - PubSubClient
   - ArduinoJson

4. **Upload:**
   ```bash
   pio run --target upload
   pio device monitor
   ```

## Multiple Devices

For each room, just change the device identity in `device_config.h`:

**Living Room:**
```cpp
const char* DEVICE_ID = "living_room_co2";
const char* DEVICE_NAME = "Living Room CO2";
```

**Bedroom:**
```cpp
const char* DEVICE_ID = "bedroom_co2";  
const char* DEVICE_NAME = "Bedroom CO2";
```

Each device appears separately in Home Assistant with 3 sensors: CO2, Temperature, Humidity.

## Home Assistant

Sensors auto-discover as:
- `sensor.living_room_co2_co2` (ppm)
- `sensor.living_room_co2_temperature` (°C)
- `sensor.living_room_co2_humidity` (%)

## Display

Shows air quality status:
- **EXCELLENT**: < 800 ppm
- **GOOD**: 800-999 ppm  
- **MODERATE**: 1000-1399 ppm
- **VENTILATE!**: ≥ 1400 ppm

## Troubleshooting

**Device not appearing in HA:**
- Check MQTT broker connection
- Verify unique `DEVICE_ID` for each device
- Check HA MQTT integration enabled

**Missing history:**
- Wait 5-10 minutes for first data points
- Check entity has `state_class: measurement`

**Connection issues:**
- Verify credentials in `device_config.h`
- Device works offline if network unavailable