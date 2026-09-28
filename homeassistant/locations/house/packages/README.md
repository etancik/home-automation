# House packages

The house configuration loads every YAML file here using
`homeassistant.packages: !include_dir_named packages`. Each package groups related
entities, helpers, scripts and automations by function. Do not include the same
files again from another configuration section.

| Package | Responsibility |
| --- | --- |
| `heating_boiler.yaml` | Boiler demand, relay control and safety watchdog |
| `heating_floor.yaml` | Floor heating thermostats |
| `heating_schedule.yaml` | Heating schedule |
| `heating_sensor_sync.yaml` | External temperature synchronization with radiator valves |
| `heating_windows.yaml` | Window handling and restoration of heating mode |
| `washing_machine.yaml` | Running/done sensor, energy integration and status logging |
| `lighting.yaml` | Kids room dimmer and evening LED strip schedule |
| `shading_v1.yaml` | Disabled-by-default sunset, night-window and morning shutter logic |
| `garage.yaml` | Garage cover and position feedback |
| `goe_charger.yaml` | Charger/controller customizations and energy dashboard sensors |
| `ev_dynamic_load_balancing.yaml` | Existing EV load-balancing configuration |
| `homekit.yaml` | House Main bridge, entity filters and HomeKit names |
| `zigbee2mqtt_deployment.yaml` | Configuration copy and add-on restart on HA startup |

Keep HomeKit in one package, preserving the bridge name, port, filters and entity
settings. Feature packages do not create additional bridges.

The main configuration retains installation settings, frontend/dashboard setup,
Recorder, logging and includes. `automations.yaml` remains an empty list available
to the UI editor; repository-managed automation belongs in the relevant package.
Device naming inventory remains in `customize.yaml`.

Preserve automation IDs and entity unique IDs when moving existing definitions.
This split changes organization only, not thresholds, triggers or actions.
Future shading packages should follow the same pattern; shading is currently a
design in the repository's `design/` directory and is not loaded by HA.

From the repository root, run `python tests/run.py` to execute the heating tests
and validate the complete house configuration in isolated HA containers.
