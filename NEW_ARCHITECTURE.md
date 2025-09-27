# Home Automation Architecture Document v2.1 - Master

## System Overview
**Primary Platform**: Home Assistant OS on Intel NUC 7  
**Configuration Approach**: YAML-based with package structure  
**UI Strategy**: Mobile-first responsive design with role-based access  
**Network**: Ubiquiti-based with VLAN segmentation for security  
**CO2 Monitoring**: LaskaKit ESP32 + SCD41 sensors with PoE networking

## Hardware Infrastructure

### Compute Platform
- **Host**: Intel NUC 7 (BOXNUC7CJYHN2)
- **OS**: Home Assistant Operating System
- **Zigbee**: SONOFF ZBDongle-E USB Plus

### Network Infrastructure
- **Gateway**: Ubiquiti UniFi Cloud Gateway Ultra
- **Wireless**: Ubiquiti UniFi AP U6+
- **Architecture**: Segmented VLANs for security isolation

### Network Segmentation Strategy
```
Internet → UCG Ultra
├── Trusted Network (10.0.1.x) - Personal devices, HA server
├── IoT Network (10.0.2.x) - Smart devices, restricted internet
├── Surveillance Network (10.0.3.x) - Cameras, doorbells
└── Guest Network (10.0.4.x) - Visitor access
```

## Software Architecture

### Core Services Stack
```yaml
Home Assistant OS
├── Home Assistant Core (primary orchestration)
├── Zigbee2MQTT Add-on (Zigbee device management)
├── Mosquitto MQTT Broker (message bus)
├── ESPHome (custom CO2 sensor management)
├── File Editor Add-on (configuration management)
└── Studio Code Server Add-on (advanced editing)
```

### Configuration Structure
Package-based YAML organization with modular files for devices, dashboards, and automations.

## User Interface Strategy
Mobile-first responsive design with role-based dashboards: Admin (full access), Spouse (control only), Kids (limited/future).

## Device Integration Plan

### Phase 1 Priority (Immediate)
| Device | Integration Method | Network Segment | Dashboard Priority |
|--------|-------------------|-----------------|-------------------|
| Shelly Plus 1 PM (Garage) | Native HA Integration | IoT Network | High - Quick Control Tile |
| Custom CO2 Sensors | ESPHome on ESP32 | IoT Network | High - Status Indicator |

### Phase 2 (Next 30 days)
| Device | Integration Method | Features |
|--------|-------------------|----------|
| go-e Charger PRO CORE | Native HA Integration | Basic energy data (no additional hw) |
| go-e Controller | Native HA Integration | Load management |
| Initial Zigbee lighting | Zigbee2MQTT | Basic automation |

### Phase 3 (60+ days)
| Device | Integration Method | Features |
|--------|-------------------|----------|
| Brink Air 70 (×2) | Custom MQTT/ESPHome | Climate integration |
| Expanded Zigbee devices | Zigbee2MQTT | Advanced automation |

### Future Consideration Devices
| Device | Current Status | Integration Potential |
|--------|----------------|----------------------|
| Amazon Blink System | Separate ecosystem | Limited HA integration |
| Gardena Smart Watering | Separate ecosystem | Good HA integration available |
| Voice Assistants | Available (Echo Dot, HomePod) | Optional future integration |

## Energy Management Strategy

### Minimal Hardware Approach
- **Primary**: go-e Controller built-in monitoring
- **Garage**: Shelly Plus 1 PM power monitoring
- **Display**: Simple dashboard cards, no real-time graphs
- **Features**: Basic consumption tracking, cost calculation

### Dashboard Energy Cards
Mobile: EV charging status, energy costs, garage power usage. Desktop: trends and optimization.

## CO2 Monitoring System - Complete Implementation

### Hardware Components (Final Selection)
| Component | Model | Quantity | Est. Cost |
|-----------|-------|----------|-----------|
| ESP32 Board | LaskaKit ESPlan (PoE + LAN8720A) | 2-3 units | ~€25 each |
| CO2 Sensor | LaskaKit SCD41 | 2-3 units | ~€35 each |
| Display | LaskaKit OLED SSD1306 | 2-3 units | ~€8 each |
| **Total per sensor** | | | **~€68** |

### Hardware Advantages
✅ **PoE Support**: Single cable for power + data  
✅ **Wired Network**: More stable than WiFi, fits network infrastructure  
✅ **SCD41 Sensor**: Latest Sensirion sensor, very accurate  
✅ **Industrial Design**: Suitable for permanent installation  
✅ **Local Supplier**: Easy procurement and support

### Network Integration
```
Sensor Placement Strategy:
ESP32 ESPlan → Ethernet → UniFi Switch → IoT VLAN (10.0.2.x)

Installation Locations:
├── Living Room (Priority 1 - Development)
├── Master Bedroom (Priority 2 - Testing)  
└── Office/Secondary room (Priority 3)
```

### Complete ESPHome Configuration
```yaml
esphome:
  name: co2-sensor-${room}
  friendly_name: "${room} CO2 Sensor"
  platform: ESP32
  board: esp32dev
  project:
    name: "homelab.co2-sensor"
    version: "1.0.0"

# Ethernet configuration for LAN8720A
ethernet:
  type: LAN8720
  mdc_pin: GPIO23
  mdio_pin: GPIO18
  clk_mode: GPIO17_OUT
  phy_addr: 0
  power_pin: GPIO12
  # Static IP assignment
  manual_ip:
    static_ip: 10.0.2.10${room_id}
    gateway: 10.0.2.1
    subnet: 255.255.255.0
    dns1: 10.0.2.1

api:
  encryption:
    key: !secret api_key

ota:
  password: !secret ota_password

logger:
  level: INFO

web_server:
  port: 80
  auth:
    username: admin
    password: !secret web_server_password

# I2C configuration
i2c:
  sda: GPIO21
  scl: GPIO22

# SCD41 sensor configuration
sensor:
  - platform: scd4x
    model: scd41
    co2:
      name: "${room} CO2"
      id: co2_sensor
      filters:
        - median:
            window_size: 3
    temperature:
      name: "${room} Temperature"
      id: temp_sensor
    humidity:
      name: "${room} Humidity" 
      id: humidity_sensor
    automatic_self_calibration: true
    update_interval: 60s

  - platform: uptime
    name: "${room} CO2 Uptime"

# Display configuration
font:
  - file: "gfonts://Roboto"
    id: font_small
    size: 10
  - file: "gfonts://Roboto"
    id: font_medium
    size: 14
  - file: "gfonts://Roboto"
    id: font_huge
    size: 28

display:
  - platform: ssd1306_i2c
    model: "SSD1306_128X64"
    address: 0x3C
    id: oled_display
    update_interval: 5s
    pages:
      - id: page_main
        lambda: |-
          // Header with room name
          it.print(0, 0, id(font_small), "${room}");
          
          // Network status
          if (id(ethernet_connected).state) {
            it.print(128, 0, id(font_small), TextAlign::TOP_RIGHT, "ETH");
          }
          
          it.line(0, 10, 128, 10);
          
          // Large CO2 reading
          if (id(co2_sensor).has_state()) {
            it.printf(64, 15, id(font_huge), TextAlign::TOP_CENTER, "%.0f", id(co2_sensor).state);
            it.print(64, 43, id(font_medium), TextAlign::TOP_CENTER, "ppm CO₂");
            
            // Status indicator
            float co2 = id(co2_sensor).state;
            const char* status = "";
            if (co2 < 800) status = "EXCELLENT";
            else if (co2 < 1000) status = "GOOD";
            else if (co2 < 1400) status = "OK";
            else status = "VENTILATE!";
            
            it.print(64, 57, id(font_small), TextAlign::TOP_CENTER, status);
          }

binary_sensor:
  - platform: status
    name: "${room} CO2 Sensor Status"

time:
  - platform: sntp
    id: sntp_time
    timezone: Europe/Prague
```

### Physical Installation Plan

#### Enclosure Modification
```yaml
3D Printed Front Panel Specifications:
├── OLED window: 24mm x 24mm opening
├── SCD41 ventilation: Grid of 2mm holes (5x2 pattern)
├── Status LED hole: 3mm diameter  
├── Room label: Embossed "LIVING ROOM" text
└── DIN rail mounting system
```

#### Standalone DIN Rail Setup
```
Hardware Requirements:
├── 35mm DIN rail (20-30cm length)
├── Wall mounting brackets
├── PoE injectors (if switches lack PoE)
└── Ethernet cables to sensor locations
```

### Home Assistant Integration & Automation

#### Dashboard Integration
Color-coded CO2 status chips (green <800ppm, yellow 800-1000, orange 1000-1400, red >1400) with room-specific entities.

#### Automation Examples
High CO2 alerts (>1200ppm) and future Brink Air 70 auto-ventilation triggers (>1000ppm when occupied).

### Development & Testing Strategy
**Phase 1 (Living Room)**: Hardware assembly, ESPHome development, HA integration, enclosure modification.  
**Phase 2 (Bedroom)**: Real-world testing, family feedback, automation development, reliability validation.

## Mobile App Strategy
iOS quick control tiles for garage (Shelly Plus 1 PM), CO2 levels, EV charging (go-e Charger PRO CORE). Role-based family access with simplified interfaces.

## Security Architecture
VLAN isolation, local-first devices, role-based user accounts, 2FA for admin, automated backups.

## Implementation Roadmap - Master Plan

### Phase 1: Foundation & Priority Devices (Weeks 1-2)
1. **HA OS installation and basic configuration**
2. **MQTT broker setup and testing**
3. **Network VLAN configuration and PoE planning**
4. **Shelly garage door integration and testing**
5. **First CO2 sensor development (Living Room)**
   - LaskaKit hardware assembly and wiring
   - ESPHome configuration and initial flash
   - Display layout testing and refinement
   - Home Assistant integration

### Phase 1.5: CO2 System Expansion (Week 3)
1. **Second CO2 sensor installation (Bedroom)**
2. **Dashboard integration and mobile optimization**
3. **Basic CO2 alerting automation**
4. **Historical data collection setup**
5. **Real-world testing and family feedback**

### Phase 2: Energy & Core Automation (Weeks 4-5)
1. **go-e Charger integration**
2. **Basic energy monitoring dashboard (minimal hardware approach)**
3. **Spouse user account and simplified interface**
4. **iOS app optimization and home screen widgets**
5. **CO2 sensor enclosure modification and permanent mounting**

### Phase 3: Advanced Features (Months 2-3)
1. **Third CO2 sensor deployment (if needed)**
2. **Zigbee2MQTT setup and first light integrations**
3. **Advanced automation rules (climate + lighting + CO2)**
4. **Desktop detailed dashboards with CO2 trends**
5. **Backup and monitoring systems**

### Phase 4: Future Expansion (Month 4+)
1. **Brink Air 70 integration with CO2 automation**
2. **Additional family member access**
3. **Evaluate external system integrations**
4. **Advanced energy optimization**
5. **Voice control evaluation**

### Immediate Procurement List
```yaml
Phase 1 Hardware Order:
├── 2x LaskaKit ESPlan ESP32 boards (~€50)
├── 2x LaskaKit SCD41 sensors (~€70)
├── 2x LaskaKit OLED displays (~€16)
├── DIN rail + mounting hardware (~€15)
├── Ethernet cables + PoE injectors (~€30)
├── Prototyping supplies (~€15)
└── Enclosure modification tools (~€20)

Total Phase 1: ~€216
```

## Success Metrics
<2s mobile response, 99%+ uptime, zero security breaches, family-friendly UI, full local control during outages.

## Technical Specifications

### CO2 Sensor Hardware Details
```yaml
Hardware Connections:
├── ESP32 ESPlan Pin Mapping:
│   ├── SCD41: VCC→3.3V, GND→GND, SDA→GPIO21, SCL→GPIO22
│   ├── OLED: VCC→3.3V, GND→GND, SDA→GPIO21, SCL→GPIO22
│   └── Ethernet: Built-in LAN8720A (PoE capable)
├── I2C Addresses:
│   ├── SCD41: 0x62
│   └── OLED SSD1306: 0x3C
└── Network Configuration:
    ├── Static IP: 10.0.2.10x (where x = room ID)
    ├── VLAN: IoT Network (10.0.2.x/24)
    └── Power: PoE (802.3af standard)
```

### ESPHome Development Environment
Home Assistant Add-on (recommended), compile/upload via `esphome` commands.

### Dashboard Breakpoints
Mobile (0-768px), Tablet (769-1024px), Desktop (1025px+).

### User Account Structure
Admin (full), Spouse (control + alerts), Kids (limited/future).

### Expected Boot Sequence (CO2 Sensors)
Ethernet connection → I2C scan finds OLED (0x3C) + SCD41 (0x62) → sensor initialization.

---

## Next Actions - Implementation Ready

### Immediate Actions (Today)
1. **Order CO2 sensor components**:
   - 2x LaskaKit ESPlan ESP32 boards
   - 2x LaskaKit SCD41 sensors
   - 2x LaskaKit OLED displays
   - DIN rail and mounting hardware

2. **Prepare development environment**:
   - Install ESPHome (Home Assistant add-on recommended)
   - Set up development workspace
   - Prepare initial configuration files

3. **Plan network infrastructure**:
   - Verify PoE capability on UniFi switches
   - Plan ethernet cable runs to sensor locations
   - Configure IoT VLAN static IP assignments

### Week 1 Development Goals
- [ ] Hardware assembly and wiring verification
- [ ] First ESP32 flash and I2C device detection
- [ ] Basic OLED display functionality
- [ ] SCD41 sensor readings and calibration
- [ ] Home Assistant integration and discovery
- [ ] Mobile dashboard basic cards

### Week 2-3 Deployment Goals  
- [ ] Living room sensor development and testing
- [ ] Bedroom sensor installation and validation
- [ ] Enclosure modification and permanent mounting
- [ ] Family member onboarding and feedback
- [ ] Basic automation rules implementation

### Confirmed Specifications
✅ **Hardware**: LaskaKit ESPlan + SCD41 + OLED (PoE networking)  
✅ **Network**: Wired Ethernet on IoT VLAN with static IPs  
✅ **Enclosure**: Existing DIN rail enclosure with 3D printed modifications  
✅ **Integration**: ESPHome → Home Assistant with mobile-first dashboard  
✅ **Budget**: ~€216 for complete 2-sensor system

