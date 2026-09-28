"""Exercise real HA + MQTT + simulated devices. Run inside the lab HA container."""
import json
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

BOILER = 'switch.laundry_room_boiler_controller_l2'
TOKEN = Path('/config/.lab-token').read_text().strip()

def api(path, data=None):
    req = Request('http://127.0.0.1:8123/api/' + path,
                  data=None if data is None else json.dumps(data).encode(),
                  headers={'Authorization': 'Bearer ' + TOKEN, 'Content-Type': 'application/json'})
    with urlopen(req, timeout=15) as response:
        return json.load(response)

def call(domain, service, **data):
    return api(f'services/{domain}/{service}', data)

def control(**data):
    call('mqtt', 'publish', topic='lab/control', payload=json.dumps(data))

def state(entity):
    return api('states/' + entity)

def expect(entity, value, timeout=35):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        result = state(entity)
        if result['state'] == value:
            return result
        time.sleep(.25)
    raise AssertionError(f'{entity}: expected {value}, got {result["state"]}')

def enabled(value):
    call('input_boolean', 'turn_on' if value else 'turn_off', entity_id='input_boolean.heating_enabled')

def reset():
    enabled(False)
    control(relay=BOILER.split('.')[1], fail='')
    call('switch', 'turn_off', entity_id=BOILER)
    expect(BOILER, 'off')
    call('script', 'heating_reset_safety')
    for room in ['bedroom', 'kids_room', 'workshop', 'entrance', 'downstairs_bathroom', 'upstairs_bathroom', 'living_room']:
        control(room=room, temperature=21, target=21, mode='heat', available='online')
    for room in ['bedroom', 'kids_room', 'workshop', 'entrance', 'kitchen', 'living_room']:
        control(room=room, window='off')
    for room in ['living_room', 'downstairs_bathroom']:
        call('climate', 'set_hvac_mode', entity_id=f'climate.{room}_floor_heating', hvac_mode='off')
    time.sleep(2)

def scenarios():
    reset()
    enabled(True)
    control(room='bedroom', mode='off', temperature=19)
    expect('climate.bedroom_radiator_heat_valve', 'off')
    time.sleep(2)
    expect(BOILER, 'off')
    control(room='bedroom', mode='heat')
    expect(BOILER, 'on')
    control(room='bedroom', temperature=20.8)
    expect('sensor.bedroom_temperature_sensor_temperature', '20.8')
    time.sleep(2)
    expect(BOILER, 'on')
    control(room='bedroom', temperature=21)
    expect(BOILER, 'off')
    print('PASS MQTT/TRV two-level hysteresis and disabled zone', flush=True)
    control(room='bedroom', mode='auto', window='on')
    expect('climate.bedroom_radiator_heat_valve', 'off')
    control(room='bedroom', window='off')
    expect('climate.bedroom_radiator_heat_valve', 'auto')
    print('PASS window restores auto', flush=True)
    call('climate', 'set_temperature', entity_id='climate.living_room_floor_heating', temperature=21)
    control(room='living_room', temperature=19)
    call('climate', 'set_hvac_mode', entity_id='climate.living_room_floor_heating', hvac_mode='heat')
    expect('switch.floor_heating_controller_l1', 'on')
    expect(BOILER, 'on')
    control(room='living_room', temperature=21.1)
    expect('switch.floor_heating_controller_l1', 'off')
    expect(BOILER, 'off')
    print('PASS native generic thermostat and floor relay', flush=True)
    control(relay=BOILER.split('.')[1], fail='on')
    control(room='bedroom', temperature=19)
    expect('input_boolean.heating_safety_lock', 'on')
    expect(BOILER, 'off')
    print('PASS unacknowledged ON locks controller', flush=True)
    reset()

def prepare_restart():
    reset()
    enabled(True)
    control(room='bedroom', temperature=19)
    expect(BOILER, 'on')
    deadline = state('input_datetime.heating_boiler_deadline')['attributes']['timestamp']
    Path('/config/.smoke-deadline').write_text(str(deadline))
    print('PASS prepared active run for real process restart', flush=True)

def verify_restart():
    expect('input_boolean.heating_controller_ready', 'on', timeout=60)
    expect(BOILER, 'on')
    expect('input_boolean.heating_safety_lock', 'off')
    assert state('input_datetime.heating_boiler_deadline')['attributes']['timestamp'] == int(float(Path('/config/.smoke-deadline').read_text()))
    print('PASS actual restart preserves deadline and heating', flush=True)
    call('input_datetime', 'set_datetime', entity_id='input_datetime.heating_boiler_deadline', timestamp=time.time()+4)
    expect('input_boolean.heating_safety_lock', 'on')
    expect(BOILER, 'off')
    time.sleep(3)
    expect(BOILER, 'off')
    print('PASS persisted deadline expires and remains locked under demand', flush=True)
    reset()


def prepare_expired_restart():
    prepare_restart()
    call('input_datetime', 'set_datetime', entity_id='input_datetime.heating_boiler_deadline', timestamp=time.time()+15)
    print('Prepared deadline that expires while HA restarts', flush=True)

def verify_expired_restart():
    expect('input_boolean.heating_controller_ready', 'on', timeout=60)
    expect('input_boolean.heating_safety_lock', 'on')
    expect(BOILER, 'off')
    time.sleep(3)
    expect(BOILER, 'off')
    print('PASS deadline expired during process restart; cold zone cannot clear lock', flush=True)
    reset()

if __name__ == '__main__':
    {'prepare-expired-restart': prepare_expired_restart, 'verify-expired-restart': verify_expired_restart, 'scenarios': scenarios, 'prepare-restart': prepare_restart, 'verify-restart': verify_restart}[sys.argv[1]]()
