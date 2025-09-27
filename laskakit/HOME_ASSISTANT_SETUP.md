# ESPlan CO2 Sensor - Home Assistant Integration

## Quick Setup

### 1. Configure Credentials
Copy the template and edit with your settings:
```bash
cp wifi_config.template.h wifi_config.h
```

Edit `wifi_config.h`:
```cpp
const char* wifi_ssid = "your_wifi_network";
const char* wifi_password = "your_wifi_password";
const char* mqtt_server = "homeassistant.local";  // Your HA IP
```

**Note**: `wifi_config.h` is gitignored for security.

### 2. Enable MQTT in Home Assistant
Ensure MQTT discovery is enabled:
```yaml
# configuration.yaml
mqtt:
  broker: localhost
  discovery: true
```

### 3. Deploy
```bash
pio run --target upload
pio device monitor  # Check connection status
```

Sensors appear automatically in Home Assistant → Devices & Services → MQTT.

## What You Get

**Device**: ESPlan CO2 Sensor (grouped in HA)
**Sensors**: CO2 (ppm), Temperature (°C), Humidity (%)
**Updates**: Every 30 seconds via MQTT

## OLED Status
- **"HA"** = Connected to Home Assistant
- **"WiFi"** = WiFi only  
- **"Local"** = Offline

## Troubleshooting

**No WiFi**: Check credentials in `wifi_config.h`
**No MQTT**: Verify `mqtt_server` IP and HA MQTT broker running
**No sensors in HA**: Check Settings → Devices & Services → MQTT

## Critical Resources
- **LaskaKit ESPlan**: https://github.com/LaskaKit/ESPlan/
- **SCD41 Datasheet**: https://sensirion.com/products/catalog/SCD41/  
- **HA MQTT Discovery**: https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery
- **PubSubClient**: https://github.com/knolleary/pubsubclient