# House packages

The house configuration loads every YAML file here using
`homeassistant.packages: !include_dir_named packages`. Each package groups related
entities, helpers, scripts and automations by function. Do not include the same
files again from another configuration section.

| Package | Responsibility |
| --- | --- |
| `heating_boiler.yaml` | Boiler demand, relay control and safety watchdog |
| `heating_floor.yaml` | Floor heating thermostats |
| `heating_sensor_sync.yaml` | External temperature synchronization with radiator valves |
| `heating_schedule.yaml` | Daily 17:00-19:00 upstairs bathroom 24 C; restores prior mode/target |
| `house_diagnostics.yaml` | Read-only room eligibility, boiler explanation, attention list, daily relay statistics and bounded event snapshots |
| `heating_windows.yaml` | Window handling and restoration of heating mode |
| `washing_machine.yaml` | Running/done sensor, energy integration and status logging |
| `lighting.yaml` | Kids room dimmer and evening LED strip schedule |
| `lighting_living_room.yaml` | Front/rear Hue groups; three detached switches, top Rear / bottom Front |
| `lighting_profiles.yaml` | Day/evening Hue profiles and per-zone manual override |
| `shading_v1.yaml` | Disabled-by-default sunset, night-window and morning shutter logic |
| `garage.yaml` | Garage cover and position feedback |
| `goe_charger.yaml` | Charger/controller customizations and energy dashboard sensors |
| `ev_dynamic_load_balancing.yaml` | Existing EV load-balancing configuration |
| `homekit.yaml` | House Main bridge, entity filters and HomeKit names |
| `zigbee2mqtt_deployment.yaml` | Configuration copy and add-on restart on HA startup |
| `backup.yaml` | Persistent notification on backup failure |

Keep HomeKit in one package, preserving the bridge name, port, filters and entity
settings. Feature packages do not create additional bridges.

The `house-debug` YAML dashboard is a quick diagnostic entry point, with heating,
attention, energy and concise events together. It does not replace HomeKit or
change boiler/charger control. The original EV dashboard remains available.
The 16 most recent observed events survive HA restarts; startup/recovery and
attribute-only changes are excluded. Reasons are snapshots, not proof of causality
or physical burner operation. Relay history and power graphs use existing Recorder
data; event explanations start when the diagnostics package is deployed.
Attention covers explicit installed inputs/battery sensors, active smoke/water
alarms, open contacts over 20 minutes, heating safety/enable, active HVAC targets
at or below 8 C, charger faults, load balancing and shaft temperature below 3 C.
This is a dashboard indication, not a new notification or safety control.

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
