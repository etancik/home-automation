# HomeKit Bedroom LED Strip - Entity ID Fix

## 🎯 GOAL: Convert `light.0x84fd27fffe92fa7c` → `light.bedroom_led_strip`

### Current Situation
- ✅ **Device configured**: Friendly name "Bedroom LED Strip" in Zigbee2MQTT
- ❌ **Entity ID**: Using hex address `light.0x84fd27fffe92fa7c`
- 🎯 **Target**: Clean entity ID `light.bedroom_led_strip`

### Solution: Force Entity Recreation

#### Option 1: Remove & Re-add Device (Recommended)
1. **Zigbee2MQTT Frontend** (http://your-ha-ip:8099)
   - Go to device `0x84fd27fffe92fa7c`
   - Click "Remove" 
   - Wait for removal confirmation

2. **Re-pair Device**
   - Put LED strip in pairing mode
   - Add device through Zigbee2MQTT
   - Verify new entity ID is `light.bedroom_led_strip`

#### Option 2: Force Entity ID via Configuration (Alternative)
Add to Zigbee2MQTT device config:
```yaml
devices:
  '0x84fd27fffe92fa7c':
    friendly_name: 'Bedroom LED Strip'
    retain: false
    description: 'Lidl LED strip behind bed for ambient lighting'
    # Force specific entity ID
    homeassistant:
      name: bedroom_led_strip
```

### ✅ HomeKit Configuration Ready
HomeKit config already updated to expect `light.bedroom_led_strip`

### Next Steps
1. Choose Option 1 or 2 above
2. Restart Home Assistant
3. Verify entity appears as `light.bedroom_led_strip`
4. Check HomeKit bridge includes the device

## Diagnostic Steps Required

### 1. Check Entity Existence in Home Assistant
Go to **Developer Tools > States** and search for:
- `light.bedroom_led_strip`
- `light.bedroom` 
- Search for any LED strip entities

### 2. Check Zigbee2MQTT Entity Creation
Go to **Settings > Devices & Services > MQTT** and look for:
- Bedroom LED Strip device
- Check if entity is created with different name

### 3. Check Entity State
If entity exists, verify:
- State is not "unavailable" or "unknown"
- Entity has proper attributes
- Entity is not disabled

### 4. Check Zigbee2MQTT Device Status
In Zigbee2MQTT frontend (port 8099):
- Verify device `0x84fd27fffe92fa7c` is online
- Check if device is properly paired
- Verify friendly name matches configuration

## Quick Fixes to Try

### Option 1: Check Entity Name in Home Assistant
```yaml
# If entity has different name, update HomeKit config:
filter:
  include_entities:
    - light.bedroom_led_strip_2  # or whatever the actual name is
```

### Option 2: Force Entity Recreation
1. Remove device from Zigbee2MQTT
2. Re-pair device
3. Restart Home Assistant

### Option 3: Manual Entity Creation
If Zigbee2MQTT isn't creating the entity, check:
- Device capabilities in Z2M
- MQTT discovery settings
- Device definition updates

## Next Steps
1. ✅ Check Developer Tools > States for exact entity name
2. ✅ Verify device status in Zigbee2MQTT
3. ✅ Update HomeKit config with correct entity name
4. ✅ Restart Home Assistant
5. ✅ Re-export config to verify entity appears in bridge