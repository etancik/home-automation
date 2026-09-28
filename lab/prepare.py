"""Build lab configuration from production heating packages; preserve runtime state."""
from pathlib import Path
import shutil

LAB=Path(__file__).resolve().parent
ROOT=LAB.parent
OUT=LAB/'.runtime/config'
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'packages').mkdir(exist_ok=True)
for path in (ROOT/'homeassistant/locations/house/packages').glob('heating_*.yaml'):
    shutil.copy2(path,OUT/'packages'/path.name)
shutil.copytree(LAB/'bootstrap',OUT/'custom_components/heating_lab',dirs_exist_ok=True)
(OUT/'configuration.yaml').write_text('''# GENERATED lab only; production registries/secrets are never copied.
homeassistant:
  name: Heating LAB
  time_zone: Europe/Prague
  unit_system: metric
  country: CZ
  packages: !include_dir_named packages
frontend:
api:
config:
history:
recorder:
  purge_keep_days: 7
logbook:
logger:
  default: warning
heating_lab:
lovelace:
  mode: yaml
''',encoding='utf-8')
(OUT/'ui-lovelace.yaml').write_text('''title: Heating LAB
views:
  - title: Heating
    cards:
      - type: markdown
        content: "Isolated simulation. No connection to household devices. Enable Heating enabled to run scenarios."
      - type: entities
        title: Controller
        entities:
          - input_boolean.heating_enabled
          - input_boolean.heating_safety_lock
          - input_datetime.heating_boiler_deadline
          - switch.laundry_room_boiler_controller_l2
          - script.heating_reset_safety
      - type: entities
        title: Bedroom simulator
        entities:
          - number.lab_bedroom_temperature
          - switch.lab_bedroom_window
          - sensor.bedroom_temperature_sensor_temperature
          - climate.bedroom_radiator_heat_valve
      - type: thermostat
        entity: climate.living_room_floor_heating
      - type: history-graph
        hours_to_show: 3
        entities:
          - switch.laundry_room_boiler_controller_l2
          - climate.bedroom_radiator_heat_valve
          - sensor.bedroom_temperature_sensor_temperature
''',encoding='utf-8')
print('Prepared',OUT)
