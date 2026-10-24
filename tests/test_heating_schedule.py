import json
from datetime import datetime
from pathlib import Path

import pytest
import yaml
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util

PACKAGE = Path(__file__).resolve().parents[1] / 'homeassistant/locations/house/packages/heating_schedule.yaml'


@pytest.fixture
async def boosts(hass, freezer):
    await hass.config.async_set_time_zone('Europe/Prague')
    freezer.move_to('2026-10-24T14:00:00Z')  # 16:00 local, outside either boost.
    config = yaml.safe_load(PACKAGE.read_text())
    config['input_boolean'] = {
        key: {} for key in ['heating_enabled', 'heating_safety_lock',
                           'heating_window_bedroom', 'heating_window_kids_room']}
    config['input_select'] = {
        'heating_saved_' + room: {'options': ['off', 'heat', 'auto']}
        for room in ['bedroom', 'kids_room']}
    calls = []

    async def climate(call):
        calls.append((call.service, dict(call.data)))
        for eid in call.data['entity_id']:
            state = hass.states.get(eid)
            attrs = dict(state.attributes)
            mode = call.data.get('hvac_mode', state.state)
            # Model the TRV recalling a separate setpoint when switching modes.
            if 'hvac_mode' in call.data:
                attrs['temperature'] = 7 if mode == 'off' else 18
            attrs.update({k: v for k, v in call.data.items() if k == 'temperature'})
            hass.states.async_set(eid, mode, attrs)

    hass.services.async_register('climate', 'set_hvac_mode', climate)
    hass.services.async_register('climate', 'set_temperature', climate)
    for room in ['bedroom', 'kids_room', 'upstairs_bathroom']:
        hass.states.async_set('climate.' + room + '_radiator_heat_valve', 'heat', {'temperature': 21})
    for room in ['bedroom', 'kids_room']:
        hass.states.async_set('binary_sensor.' + room + '_window_sensor_contact', 'off')
    for domain in ['input_boolean', 'input_select', 'input_text', 'script', 'automation']:
        assert await async_setup_component(hass, domain, {domain: config[domain]})
    await hass.services.async_call('input_boolean', 'turn_on', {'entity_id': 'input_boolean.heating_enabled'}, blocking=True)
    await hass.async_block_till_done()
    calls.clear()
    yield calls
    await hass.services.async_call('automation', 'turn_off', {
        'entity_id': 'automation.heating_morning_rooms_and_evening_bathing', 'stop_actions': True}, blocking=True)


async def reconcile(hass):
    await hass.services.async_call('automation', 'trigger', {
        'entity_id': 'automation.heating_morning_rooms_and_evening_bathing'}, blocking=True)
    await hass.async_block_till_done()


def valve(hass, room):
    return hass.states.get('climate.' + room + '_radiator_heat_valve')


def saved(hass, room):
    return json.loads(hass.states.get('input_text.heating_boost_saved_' + room).state)


@pytest.mark.parametrize('start,end,rooms,target', [
    ('2026-10-24T04:00:00Z', '2026-10-24T05:00:00Z', ['bedroom', 'kids_room'], 22),
    ('2026-10-24T15:00:00Z', '2026-10-24T17:00:00Z', ['upstairs_bathroom'], 24),
    # After the DST switch, the same local morning starts an hour later in UTC.
    ('2026-10-25T05:00:00Z', '2026-10-25T06:00:00Z', ['bedroom', 'kids_room'], 22),
])
async def test_daily_boost_and_restore_original_targets(hass, boosts, freezer, start, end, rooms, target):
    freezer.move_to(start)
    await reconcile(hass)
    for room in rooms:
        assert valve(hass, room).state == 'heat'
        assert valve(hass, room).attributes['temperature'] == target
        assert saved(hass, room)['temperature'] == 21
    original = {room: saved(hass, room) for room in rooms}
    await reconcile(hass)  # A restart/reconciliation must not overwrite the backup.
    assert {room: saved(hass, room) for room in rooms} == original
    assert all(valve(hass, room).attributes['temperature'] == 21
               for room in ['bedroom', 'kids_room', 'upstairs_bathroom'] if room not in rooms)
    freezer.move_to(end)
    await reconcile(hass)
    for room in rooms:
        assert valve(hass, room).attributes['temperature'] == 21
        assert saved(hass, room) == {}


@pytest.mark.parametrize('mode,temp', [('off', 7), ('auto', 19.5)])
async def test_restore_original_mode_and_mode_specific_target(hass, boosts, freezer, mode, temp):
    hass.states.async_set('climate.bedroom_radiator_heat_valve', mode, {'temperature': temp})
    freezer.move_to('2026-10-24T04:30:00Z')
    await reconcile(hass)
    assert valve(hass, 'bedroom').state == 'heat'
    assert valve(hass, 'bedroom').attributes['temperature'] == 22
    freezer.move_to('2026-10-24T05:00:00Z')
    await reconcile(hass)
    assert valve(hass, 'bedroom').state == mode
    assert valve(hass, 'bedroom').attributes['temperature'] == temp


@pytest.mark.parametrize('guard,value', [('heating_enabled', 'off'), ('heating_safety_lock', 'on')])
async def test_boost_respects_global_heating_guards(hass, boosts, freezer, guard, value):
    hass.states.async_set('input_boolean.' + guard, value)
    freezer.move_to('2026-10-24T15:00:00Z')
    await reconcile(hass)
    assert valve(hass, 'upstairs_bathroom').attributes['temperature'] == 21
    assert boosts == []


async def test_open_window_delays_start_and_restores_safely_at_end(hass, boosts, freezer):
    contact = 'binary_sensor.bedroom_window_sensor_contact'
    block = 'input_boolean.heating_window_bedroom'
    hass.states.async_set(contact, 'on')
    freezer.move_to('2026-10-24T04:00:00Z')
    await reconcile(hass)
    assert valve(hass, 'bedroom').attributes['temperature'] == 21
    hass.states.async_set(contact, 'off')
    await reconcile(hass)
    assert valve(hass, 'bedroom').attributes['temperature'] == 22
    # Model the window controller turning the radiator off during the boost.
    hass.states.async_set(contact, 'on')
    hass.states.async_set(block, 'on')
    hass.states.async_set('climate.bedroom_radiator_heat_valve', 'off', {'temperature': 7})
    freezer.move_to('2026-10-24T05:00:00Z')
    await reconcile(hass)
    assert valve(hass, 'bedroom').state == 'off'
    assert hass.states.get('input_select.heating_saved_bedroom').state == 'heat'
    assert saved(hass, 'bedroom')['temperature'] == 21
    # The window controller later restores heat, potentially recalling the boost target.
    hass.states.async_set(contact, 'off')
    hass.states.async_set(block, 'off')
    hass.states.async_set('climate.bedroom_radiator_heat_valve', 'heat', {'temperature': 22})
    await reconcile(hass)
    assert valve(hass, 'bedroom').attributes['temperature'] == 21
    assert saved(hass, 'bedroom') == {}


async def test_expired_backup_recovers_after_offline_end_even_next_day(hass, boosts, freezer):
    backup = {'mode': 'auto', 'temperature': 19.5,
              'until': datetime.fromisoformat('2026-10-23T17:00:00+00:00').timestamp()}
    await hass.services.async_call('input_text', 'set_value', {
        'entity_id': 'input_text.heating_boost_saved_upstairs_bathroom', 'value': json.dumps(backup)}, blocking=True)
    hass.states.async_set('climate.upstairs_bathroom_radiator_heat_valve', 'unavailable')
    freezer.move_to('2026-10-24T15:30:00Z')
    await reconcile(hass)
    assert saved(hass, 'upstairs_bathroom') == backup
    hass.states.async_set('climate.upstairs_bathroom_radiator_heat_valve', 'heat', {'temperature': 24})
    await reconcile(hass)
    # A time-pattern tick can immediately start today's boost after recovery.
    # The expired baseline must be restored first and saved again, never replaced by 24.
    assert boosts[:2] == [
        ('set_hvac_mode', {'entity_id': ['climate.upstairs_bathroom_radiator_heat_valve'], 'hvac_mode': 'auto'}),
        ('set_temperature', {'entity_id': ['climate.upstairs_bathroom_radiator_heat_valve'], 'temperature': 19.5}),
    ]
    await reconcile(hass)
    assert saved(hass, 'upstairs_bathroom')['temperature'] == 19.5
    assert valve(hass, 'upstairs_bathroom').attributes['temperature'] == 24
