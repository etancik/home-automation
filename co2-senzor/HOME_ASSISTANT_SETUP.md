# CO2 Sensor Setup - PlatformIO + Home Assistant

## Quick Deploy

```bash
# 1. Copy config for target location
cd /Users/i343783/git/experiments/home-automation/co2-senzor
cp src/device_config_living_room.h src/device_config.h

# 2. Upload firmware (ESP32 via USB)
~/.platformio/penv/bin/platformio run --target upload --upload-port /dev/cu.usbserial-XXXXXXXX
```

**Result**: Auto-connects to WiFi → MQTT → Home Assistant → HomeKit

## Current Status

**Active Sensors:**
- Bedroom: `A0:B7:65:4B:6A:CC` ✅
- Living Room: `10:97:BD:CD:7E:C0` ✅ 

**Tech Stack:**
- PlatformIO + ESP32 Platform v6.4.0 (Python 3.9 compatible)
- MQTT Discovery → HA → HomeKit bridge (port 21064)

## Issues & Fixes

**Upload fails**: Use compatible ESP32 platform v6.4.0, not newer versions  
**Not in iOS Home**: Restart HomeKit integration in HA  
**Device not found**: Check USB cable (data, not power-only)