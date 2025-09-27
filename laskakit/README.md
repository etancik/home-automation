# LaskaKit ESP32 Development

This directory contains all development files for LaskaKit ESPlan ESP32 hardware.

## Files

- **`ESPLAN_NOTES.md`** - Critical pin discoveries and GitHub repository links
- **`platformio.ini`** - PlatformIO project configuration
- **`src/main.cpp`** - Working OLED test code with ESPlan-specific pins

## Key Discovery

ESPlan boards use **GPIO33/32** for I2C (not standard GPIO21/22).

## Quick Start

```bash
cd laskakit
.venv/bin/pio run --target upload
.venv/bin/pio device monitor --baud 115200
```

Should display "Hello!" and "ESPlan Working" on connected OLED display.