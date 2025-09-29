# Home Automation Architecture Document v2.1 - Master

> **⚠️ CRITICAL: Hardware Specifications Protection**  
> The hardware components, links, and specific device models listed in this document are based on actual procurement and testing. **DO NOT MODIFY** these specifications, part numbers, or supplier links without explicit approval. Any changes to hardware specifications must be explicitly requested and approved.

## System Overview
**Primary Platform**: Home Assistant OS on Intel NUC 7  
**Configuration Approach**: YAML-based with package structure  
**UI Strategy**: Mobile-first responsive design### Next Actions - Implementation Ready

### Immediate Actions (Today)
1. **Set up GitOps workflow**:
   - Create dedicated HA config repository
   - Configure Git Pull add-on
   - Test local edit → Git push → HA pull workflow

2. **Deploy existing CO2 sensors**:
   - Flash current PlatformIO code to devices
   - Configure MQTT integration
   - Add to Home Assistant dashboard

3. **Plan network infrastructure**:
   - Configure IoT VLAN for devices
   - Set up static IP assignments
   - Test connectivity and MQTT communicationccess  
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
├── Git Pull Add-on (configuration as code)
└── Custom CO2 Sensors (PlatformIO/Arduino via MQTT)
```

### Configuration Structure
- **GitOps Workflow**: Edit locally, push to Git, auto-pull to HA
- **Package-based YAML**: Modular organization for devices, dashboards, automations
- **No Editor Add-ons needed**: Edit from your PC, Git handles deployment

## User Interface Strategy
Mobile-first responsive design with role-based dashboards: Admin (full access), Spouse (control only), Kids (limited/future).

## Device Integration Plan

### Phase 1 Priority (Immediate)
| Device | Integration Method | Network Segment | Status |
|--------|-------------------|-----------------|--------|
| Shelly Plus 1 PM (Garage) | Native HA Integration | IoT Network | Planned |
| Custom CO2 Sensors | PlatformIO + MQTT | IoT Network | In Development |

### Phase 2 (Next 30 days)
| Device | Integration Method | Features |
|--------|-------------------|----------|
| go-e Charger PRO CORE | Native HA Integration | Basic energy data (no additional hw) |
| go-e Controller | Native HA Integration | Load management |
| Initial Zigbee lighting | Zigbee2MQTT | Basic automation |

### Phase 3 (60+ days)
| Device | Integration Method | Features |
|--------|-------------------|----------|
| Brink Air 70 (×2) | RS485/Modbus RTU via ESPlan | Climate integration, CO2-triggered ventilation |
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

## CO2 Monitoring System - LaskaKit Hardware

### Hardware Components (Replication Order)
| Component | Code | Price | Link |
|-----------|------|-------|------|
| LaskaKit ESPlan ESP32 LAN8720A RS485 PoE | LA100133I | 648 Kč | [Link](https://www.laskakit.cz/laskakit-esplan-esp32-lan8720a-max485-poe/) |
| LaskaKit SCD41 CO2 Sensor | LA131062 | 768 Kč | [Link](https://www.laskakit.cz/laskakit-scd41-senzor-co2--teploty-a-vlhkosti-vzduchu/) |
| LaskaKit OLED Display 128x64 | LA141102B | 98 Kč | [Link](https://www.laskakit.cz/laskakit-oled-displej-128x64-0-96-i2c/) |
| LaskaKit Enclosure for ESPlan | LA270021W | 148 Kč | [Link](https://www.laskakit.cz/laskakit-krabicka-pro-laskakit-esplan/) |
| DIN Rail Mount | LA220006 | 28 Kč | [Link](https://www.laskakit.cz/drzak-pcb-na-35mm-din-listu/) |
| WiFi Antenna 2.4G U.FL | LA162036 | 18 Kč | [Link](https://www.laskakit.cz/mini-antena-3db-2-4g-u-fl--ipex--konektor/) |
| I²C Cable JST-SH 4-pin 10cm | LA150124B | 12 Kč | [Link](https://www.laskakit.cz/--sup--stemma-qt--qwiic-jst-sh-4-pin-kabel-10cm/) |
| **Total per sensor** | | **1,720 Kč** | |

> **Note**: ESPlan model chosen for RS485 capability to enable future Brink Air 70 ventilation integration via Modbus RTU protocol. Standard ESP32 boards cost ~300 Kč less but lack RS485 interface needed for HVAC communication.

### Implementation
- **Software**: PlatformIO + Arduino framework (existing code in `/co2-senzor/`)
- **Integration**: MQTT with Home Assistant auto-discovery
- **Network**: PoE via LAN8720A chipset on IoT VLAN

## Physical Installation Plan

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

### Phase 1: Foundation & Priority Devices
1. **HA OS installation and basic configuration**
2. **Git Pull add-on setup for configuration as code**
3. **MQTT broker setup and testing**
4. **Network VLAN configuration**
5. **Shelly garage door integration**
6. **CO2 sensor deployment** (using existing PlatformIO code)
   - Deploy to first location (living room/bedroom)
   - Configure MQTT integration with HA
   - Set up mobile dashboard cards

### Phase 1.5: CO2 System Expansion
1. **Second CO2 sensor deployment**
2. **Dashboard integration and mobile optimization**
3. **Basic CO2 alerting automation**
4. **Historical data collection setup**

### Phase 2: Energy & Core Automation
1. **go-e Charger integration**
2. **Basic energy monitoring dashboard**
3. **Spouse user account and simplified interface**
4. **iOS app optimization and home screen widgets**

### Phase 3: Advanced Features
1. **Third CO2 sensor deployment (if needed)**
2. **Zigbee2MQTT setup and first light integrations**
3. **Advanced automation rules (climate + lighting + CO2)**
4. **Desktop detailed dashboards with trends**

### Phase 4: Future Expansion
1. **Brink Air 70 integration with CO2 automation**
2. **Additional family member access**
3. **Evaluate external system integrations**
4. **Advanced energy optimization**

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

### Development Goals
- [ ] GitOps workflow setup and testing
- [ ] CO2 sensor MQTT integration with Home Assistant
- [ ] Mobile dashboard basic cards
- [ ] Network VLAN configuration
- [ ] Basic automation rules

### Deployment Goals  
- [ ] Multiple CO2 sensor deployment
- [ ] Advanced dashboard configuration
- [ ] Family member onboarding and feedback
- [ ] Automation rules implementation
- [ ] Historical data collection setup

### Confirmed Specifications
✅ **Hardware**: LaskaKit ESPlan + SCD41 + OLED (PoE networking)  
✅ **Software**: PlatformIO with Arduino framework + MQTT  
✅ **Integration**: MQTT with Home Assistant auto-discovery  
✅ **Configuration**: GitOps workflow for infrastructure as code  
✅ **Status**: Hardware procured (1,682 Kč), ready for deployment  
✅ **Enclosure**: LaskaKit professional enclosure with DIN rail mounting

