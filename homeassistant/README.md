# Multi-Location Home Assistant Configuration

This directory contains a complete multi-location Home Assistant setup using Git subtree for deployment.

## Structure

```
homeassistant/
├── core/                          # Shared components for all locations
│   ├── packages/                  # Core packages (CO2 monitoring, areas)
│   ├── templates/                 # Reusable automation templates
│   └── automations/               # Core automation patterns
├── locations/
│   ├── house/                     # House-specific configuration
│   │   ├── configuration.yaml     # Main config with core includes
│   │   ├── automations.yaml       # House automations
│   │   ├── customize.yaml         # Device customizations
│   │   ├── scripts.yaml           # House scripts
│   │   └── scenes.yaml            # House scenes
│   └── flat/                      # Flat-specific configuration (template)
│       ├── configuration.yaml     # Main config (dormant)
│       ├── automations.yaml       # Flat automations (empty)
│       ├── customize.yaml         # Device customizations (template)
│       ├── scripts.yaml           # Flat scripts (empty)
│       └── scenes.yaml            # Flat scenes (empty)
└── deployment/                    # Deployment configurations and scripts
    ├── house.yaml                 # House deployment config
    ├── flat.yaml                  # Flat deployment config
    └── README.md                  # Deployment instructions
```

## Key Features

### Multi-Location Support
- **Shared Core**: Common packages and templates in `/core/`
- **Location-Specific**: Separate configurations for house and flat
- **Git Subtree Deployment**: Each location has its own branch

### Working Components
- **CO2 Monitoring**: LaskaKit ESPlan + SCD41 sensors via MQTT
- **Area Management**: Consistent area definitions across locations
- **Person Tracking**: Shared person entities
- **HomeKit Integration**: Single bridge per location (no more confusion!)

### Safety Features
- **Secret Management**: Location-specific secrets files
- **No Hardcoded Secrets**: All sensitive data in secrets.yaml
- **Deployment Safety**: Testing on house before flat deployment

## Current Status

### ✅ Ready for House Deployment
- Core packages implemented
- House configuration complete
- CO2 sensors working (bedroom_co2_sensor)
- Deployment scripts ready

### ⚠️ Needs Device Renaming First
These Zigbee devices need friendly names in Zigbee2MQTT:
- `0x54ef441000edf7c1` → `bedroom_weather_sensor`
- `0xb4e3f9fffea76436` → `living_room_light_1`

### 🚧 Flat Configuration (Dormant)
- Template structure created
- All files are empty/dormant
- Ready for future activation

## Deployment Process

1. **Setup**: Follow `/deployment/README.md`
2. **House First**: Deploy and test house configuration
3. **Flat Later**: Activate flat when second location is ready

## Migration from Current Config

This replaces the messy current configuration with:
- Clean device names instead of hex IDs
- Single HomeKit bridge per location
- Proper area organization
- Configuration as code with Git

## Next Steps

1. Rename Zigbee devices to friendly names
2. Create Git subtree branches
3. Deploy to house NUC
4. Test and refine
5. Prepare flat configuration when needed