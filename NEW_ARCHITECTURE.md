# Multi-Location Home Automation Architecture v2.0

> **⚠️ CRITICAL: Hardware Specifications Protection**  
> The hardware components, links, and specific device models listed in this document are based on actual procurement and testing. **DO NOT MODIFY** these specifications, part numbers, or supplier links without explicit approval. Any changes to hardware specifications must be explicitly requested and approved.

## System Overview
**Deployment Model**: Dual Independent HA Instances (House + Flat)  
**Primary Platform**: Home Assistant OS on Intel NUC 7 (both locations)  
**Configuration Approach**: Shared core patterns with location-specific deployment  
**UI Strategy**: iOS Home as primary family interface + HA for power users  
**Network**: VLAN segmentation at both locations  
**Device Standardization**: Same CO2 sensors, reusable automation patterns

## Multi-Location Design Principles

### 1. **House = Full Complexity, Flat = Essential + Growth Ready**
- House: Complete automation (EV charging, garage, garden, advanced scheduling)
- Flat: Core features (lights, CO2) with dormant advanced features ready to activate

### 2. **iOS Home as Family Interface**
- Primary control method for family members
- HA backend for monitoring, troubleshooting, and power user features
- Clean device organization (no random IDs or duplicates)

### 3. **Shared Core Architecture**
- Common automation patterns extracted into reusable templates
- Location-specific parameters and device instances
- Core development at house, stable deployment to flat

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

## Multi-Location Configuration Organization

### Repository Structure
```
home-automation/
├── README.md
├── core/                           # Shared core patterns
│   ├── packages/
│   │   ├── co2_monitoring.yaml     # CO2 sensor automation templates
│   │   ├── energy_management.yaml  # EV charging, power monitoring patterns
│   │   ├── lighting_automation.yaml # Zigbee light automation patterns
│   │   ├── climate_control.yaml    # HVAC and ventilation patterns
│   │   └── security_base.yaml      # Basic security automation patterns
│   ├── templates/
│   │   ├── device_discovery.yaml   # MQTT auto-discovery templates
│   │   ├── dashboard_cards.yaml    # Reusable dashboard components
│   │   └── notification_patterns.yaml # Alert and notification templates
│   └── scripts/
│       ├── homekit_sync.yaml       # iOS Home synchronization patterns
│       └── backup_automation.yaml  # Automated backup scripts
├── locations/
│   ├── house/                      # Primary location (full complexity)
│   │   ├── configuration.yaml      # Main HA config with core imports
│   │   ├── secrets.yaml           # Location-specific credentials
│   │   ├── customize.yaml         # Entity customizations
│   │   ├── packages/
│   │   │   ├── garage_control.yaml        # Shelly garage door + sensors
│   │   │   ├── ev_charging.yaml          # go-e Charger + Controller
│   │   │   ├── hvac_integration.yaml     # Brink Air 70 (×2) via RS485
│   │   │   ├── garden_automation.yaml    # Future Gardena integration
│   │   │   └── security_advanced.yaml    # Advanced security features
│   │   ├── dashboards/
│   │   │   ├── mobile_main.yaml          # Primary mobile dashboard
│   │   │   ├── desktop_detailed.yaml     # Detailed desktop interface
│   │   │   ├── energy_management.yaml    # EV + power monitoring
│   │   │   └── climate_overview.yaml     # CO2 + HVAC dashboard
│   │   └── automations/
│   │       ├── co2_ventilation.yaml      # CO2 → Brink Air automation
│   │       ├── ev_smart_charging.yaml    # Time-based EV charging
│   │       ├── presence_lighting.yaml    # Advanced lighting automation
│   │       └── energy_optimization.yaml  # Load management automation
│   └── flat/                       # Secondary location (essential + dormant)
│       ├── configuration.yaml      # Main HA config with core imports
│       ├── secrets.yaml           # Location-specific credentials
│       ├── customize.yaml         # Entity customizations
│       ├── packages/
│       │   ├── basic_lighting.yaml       # Essential Zigbee lights only
│       │   ├── co2_monitoring.yaml       # CO2 sensors (same as house)
│       │   └── dormant_features.yaml     # Advanced features (disabled)
│       ├── dashboards/
│       │   ├── mobile_simple.yaml        # Simplified mobile interface
│       │   └── basic_overview.yaml       # Essential controls only
│       └── automations/
│           ├── co2_alerts.yaml           # Basic CO2 monitoring
│           ├── simple_lighting.yaml      # Basic light automation
│           └── presence_detection.yaml   # Simple presence-based control
└── deployment/
    ├── house_deploy.sh             # House-specific deployment script
    ├── flat_deploy.sh              # Flat-specific deployment script
    └── sync_core.sh                # Core pattern synchronization
```

### Configuration Pattern Examples

#### Core Template Pattern (co2_monitoring.yaml)
```yaml
# /core/packages/co2_monitoring.yaml
homeassistant:
  customize_glob:
    "sensor.*_co2":
      device_class: carbon_dioxide
      unit_of_measurement: "ppm"
      icon: mdi:molecule-co2

template:
  - sensor:
      - name: "{{ location }}_{{ room }}_co2_status"
        state: >
          {% set co2 = states('sensor.' + location + '_' + room + '_co2') | int(0) %}
          {% if co2 < 800 %}Good
          {% elif co2 < 1000 %}Acceptable  
          {% elif co2 < 1400 %}Poor
          {% else %}Very Poor{% endif %}
        attributes:
          color: >
            {% set co2 = states('sensor.' + location + '_' + room + '_co2') | int(0) %}
            {% if co2 < 800 %}green
            {% elif co2 < 1000 %}yellow
            {% elif co2 < 1400 %}orange
            {% else %}red{% endif %}

automation:
  - alias: "CO2 High Alert - {{ location }} {{ room }}"
    trigger:
      - platform: numeric_state
        entity_id: "sensor.{{ location }}_{{ room }}_co2"
        above: "{{ high_threshold | default(1200) }}"
        for: "{{ alert_delay | default('00:05:00') }}"
    action:
      - service: notify.family
        data:
          title: "High CO2 Detected"
          message: "{{ room | title }} CO2: {{ trigger.to_state.state }}ppm"
```

#### Location-Specific Implementation (house/packages/garage_control.yaml)
```yaml
# /locations/house/packages/garage_control.yaml
# Import core patterns
<<: !include ../../core/packages/energy_management.yaml

# Location-specific device configuration
switch:
  - platform: mqtt
    name: "House Garage Door"
    state_topic: "shelly/garage/relay/0"
    command_topic: "shelly/garage/relay/0/command"
    device:
      identifiers: ["house_garage_shelly"]
      manufacturer: "Allterco"
      model: "Shelly Plus 1 PM"

sensor:
  - platform: mqtt
    name: "House Garage Power"
    state_topic: "shelly/garage/relay/0/power"
    unit_of_measurement: "W"
    device_class: power

# Location-specific automation
automation:
  - alias: "House Garage Auto Close"
    trigger:
      - platform: state
        entity_id: switch.house_garage_door
        to: 'on'
        for: '00:30:00'
    condition:
      - condition: time
        after: '22:00:00'
        before: '06:00:00'
    action:
      - service: switch.turn_off
        entity_id: switch.house_garage_door
```

#### Flat Configuration (flat/packages/dormant_features.yaml)
```yaml
# /locations/flat/packages/dormant_features.yaml
# Dormant advanced features - ready to activate when needed

# EV Charging (dormant - no hardware yet)
# <<: !include ../../core/packages/energy_management.yaml

# HVAC Integration (dormant - no Brink Air units yet)  
# <<: !include ../../core/packages/climate_control.yaml

# Garage Control (dormant - no garage)
# <<: !include ../../core/packages/garage_automation.yaml

# Placeholder entities for future activation
input_boolean:
  flat_ev_charging_enabled:
    name: "EV Charging Features"
    initial: false
    icon: mdi:car-electric
    
  flat_hvac_automation_enabled:
    name: "HVAC Automation" 
    initial: false
    icon: mdi:air-conditioner

# Simple automation to activate dormant features
automation:
  - alias: "Activate EV Features"
    trigger:
      - platform: state
        entity_id: input_boolean.flat_ev_charging_enabled
        to: 'on'
    action:
      - service: homeassistant.reload_config_entry
        data:
          entry_id: "{{ config_entry_id }}"
      - service: persistent_notification.create
        data:
          title: "Feature Activated"
          message: "EV charging features are now active. Please restart Home Assistant."
```

### Deployment Strategy

#### Core Pattern Synchronization
- **Development**: Primary development at house location
- **Testing**: Validate patterns with full hardware suite
- **Extraction**: Move proven automations to `/core/` templates
- **Deployment**: Sync core changes to flat location
- **Customization**: Apply location-specific parameters

#### Git Workflow for Multi-Location
```bash
# Development workflow
git checkout -b feature/co2-ventilation-automation
# Develop and test at house location
git add locations/house/automations/co2_ventilation.yaml
git commit -m "Add CO2 ventilation automation for house"

# Extract to core pattern
git add core/packages/co2_monitoring.yaml
git commit -m "Extract CO2 monitoring to core template"

# Apply to flat location with modifications
git add locations/flat/packages/co2_monitoring.yaml  
git commit -m "Apply CO2 monitoring to flat (alerts only)"

git push origin feature/co2-ventilation-automation
# Deploy to both locations via Git Pull add-on
```

#### Location-Specific Secrets Management
```yaml
# /locations/house/secrets.yaml
mqtt_username: "house_ha_user"
mqtt_password: !secret house_mqtt_password
homekit_pin: !secret house_homekit_pin
notification_webhook: !secret house_webhook_url

# /locations/flat/secrets.yaml  
mqtt_username: "flat_ha_user"
mqtt_password: !secret flat_mqtt_password
homekit_pin: !secret flat_homekit_pin
notification_webhook: !secret flat_webhook_url
```

This organization enables:
- **Shared Development**: Core patterns developed once, deployed everywhere
- **Location Flexibility**: Each location can customize without affecting others
- **Growth Ready**: Dormant features ready to activate when hardware is added
- **Maintainability**: Clear separation between shared and location-specific code
- **Version Control**: Proper Git workflow for multi-location deployment

## User Interface Strategy
Mobile-first responsive design with role-based dashboards: Admin (full access), Spouse (control only), Kids (limited/future).

## Device Integration Status

### Current Implementation Status
| Device | Integration Method | Status | Next Steps |
|--------|-------------------|--------|------------|
| CO2 Sensors | PlatformIO + MQTT | ✅ Working | Dashboard optimization, alerts |
| Zigbee Lights | Zigbee2MQTT | 🔄 Needs HomeKit cleanup | Entity naming, iOS Home reset |
| Shelly Plus 1 PM (Garage) | Native HA Integration | 📋 Planned | After light integration |
| go-e Charger PRO CORE | Native HA Integration | 📋 Future | Basic energy monitoring |
| go-e Controller | Native HA Integration | 📋 Future | Load management |
| Brink Air 70 (×2) | RS485/Modbus RTU via ESPlan | 📋 Future | Climate integration, CO2-triggered ventilation |

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
**Current Status**: CO2 sensors deployed and working with PlatformIO + MQTT auto-discovery.  
**Next Phase**: HomeKit integration cleanup, Zigbee light organization, garage door integration.

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

### Dashboard Breakpoints
Mobile (0-768px), Tablet (769-1024px), Desktop (1025px+).

### User Account Structure
Admin (full), Spouse (control + alerts), Kids (limited/future).

### Expected Boot Sequence (CO2 Sensors)
Ethernet connection → I2C scan finds OLED (0x3C) + SCD41 (0x62) → sensor initialization.

---

## Current Implementation Tasks

### Immediate Actions
1. **HA Configuration Export & Cleanup**:
   - Export current HA configuration via File Editor or backup
   - Review current entity naming and HomeKit exposure
   - Clean up duplicated or orphaned devices

2. **HomeKit Integration Reset**:
   - Remove current HomeKit integration 
   - Standardize entity naming conventions
   - Re-add devices to iOS Home with proper organization

3. **Zigbee Light Integration**:
   - Configure SONOFF ZBDongle-E USB Plus with Zigbee2MQTT
   - Pair existing Zigbee lights with proper naming
   - Expose to iOS Home with consistent naming pattern

### Near-term Goals
- [ ] HA configuration export and review
- [ ] HomeKit integration cleanup and reset
- [ ] Zigbee2MQTT setup with SONOFF ZBDongle-E USB Plus
- [ ] Zigbee light integration with proper naming
- [ ] iOS Home organization and family access

### Future Implementation Phases

#### Phase 1: Foundation Completion
- Shelly Plus 1 PM garage door integration
- CO2 sensor dashboard optimization and alerting
- GitOps workflow setup for configuration management

#### Phase 2: Energy & Advanced Automation  
- go-e Charger PRO CORE and go-e Controller integration
- Energy monitoring dashboard with Shelly Plus 1 PM power monitoring
- Advanced lighting automation patterns

#### Phase 3: HVAC Integration
- Brink Air 70 (×2) integration via RS485/Modbus RTU via ESPlan
- CO2-triggered ventilation automation
- Climate optimization with combined sensor data

#### Phase 4: Multi-Location Deployment
- Extract core automation patterns into reusable templates
- Deploy shared configuration to flat location
- Implement location-specific customizations

### Confirmed Current Status
✅ **Hardware**: LaskaKit ESPlan + SCD41 + OLED (PoE networking) - procured (1,682 Kč)  
✅ **Software**: PlatformIO + Arduino framework + MQTT auto-discovery - working  
✅ **CO2 Integration**: MQTT with Home Assistant auto-discovery - deployed  
🔄 **HomeKit**: Needs cleanup and proper organization  
📋 **Configuration**: GitOps workflow planned for infrastructure as code

