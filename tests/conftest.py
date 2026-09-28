from pathlib import Path
import pytest
import yaml
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ROOT / 'homeassistant/locations/house/packages'
BOILER = 'switch.laundry_room_boiler_controller_l2'
ROOMS = ['bedroom', 'kids_room', 'workshop', 'entrance', 'downstairs_bathroom', 'upstairs_bathroom']
CONTACTS = ['bedroom_window', 'kids_room_window', 'workshop_window', 'entrance_door', 'kitchen_window', 'living_room_door']

def package(name):
    return yaml.safe_load((PACKAGES / f'heating_{name}.yaml').read_text())

class Rig:
    def __init__(self, hass):
        self.hass = hass
        self.calls = []
        self.failed = set()

    def state(self, eid, value, **attributes):
        old = self.hass.states.get(eid)
        attrs = dict(old.attributes) if old else {}
        self.hass.states.async_set(eid, value, {**attrs, **attributes})

    def room(self, room='bedroom', temp=19, mode='heat', action='heating', target=21):
        self.state(f'sensor.{room}_temperature_sensor_temperature', str(temp))
        self.state(f'climate.{room}_radiator_heat_valve', mode,
                   current_temperature=temp, temperature=target, hvac_action=action)

    async def settle(self):
        await self.hass.async_block_till_done()

    async def enabled(self, enabled=True):
        await self.hass.services.async_call('input_boolean', 'turn_on' if enabled else 'turn_off',
            {'entity_id': 'input_boolean.heating_enabled'}, blocking=True)
        await self.settle()

@pytest.fixture
async def rig(hass: HomeAssistant):
    r = Rig(hass)
    for room in ROOMS:
        r.room(room, temp=21, action='idle')
    r.state('sensor.living_room_temperature_sensor_temperature', '21')
    for room in ['living_room', 'downstairs_bathroom']:
        r.state(f'climate.{room}_floor_heating', 'heat', current_temperature=21, temperature=21, hvac_action='idle')
    for entity in [BOILER, 'switch.floor_heating_controller_l1', 'switch.floor_heating_controller_l2']:
        r.state(entity, 'off')
    for c in CONTACTS:
        r.state(f'binary_sensor.{c}_sensor_contact', 'off')
    async def relay(call):
        targets = call.data['entity_id']
        if isinstance(targets, str): targets = [targets]
        for target in targets:
            state = 'on' if call.service == 'turn_on' else 'off'
            r.calls.append((target, state))
            if state not in r.failed:
                r.state(target, state)
    async def climate(call):
        targets = call.data['entity_id']
        if isinstance(targets, str): targets = [targets]
        for target in targets:
            mode = call.data['hvac_mode']
            r.state(target, mode, hvac_action='idle' if mode == 'off' else 'heating')
    assert await async_setup_component(hass, 'homeassistant', {})
    assert await async_setup_component(hass, 'persistent_notification', {})
    for service in ['turn_on','turn_off']:
        hass.services.async_register('switch', service, relay)
    hass.services.async_register('climate','set_hvac_mode',climate)
    config = package('boiler')
    windows = package('windows')
    config['input_boolean'].update(windows['input_boolean'])
    config['input_select'] = windows['input_select']
    config['automation'] += windows['automation']
    for domain in ['input_boolean', 'input_select', 'input_datetime', 'script']:
        assert await async_setup_component(hass, domain, {domain: config[domain]})
    await hass.services.async_call('input_datetime', 'set_datetime',
        {'entity_id':'input_datetime.heating_boiler_deadline','timestamp':0},blocking=True)
    assert await async_setup_component(hass, 'automation', {'automation':config['automation']})
    await r.settle()
    await hass.async_start()
    yield r
    await hass.services.async_call('automation', 'turn_off', {'entity_id': [s.entity_id for s in hass.states.async_all('automation')], 'stop_actions': True}, blocking=True)
    await hass.async_stop(force=True)
