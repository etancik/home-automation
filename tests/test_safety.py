import pytest
from conftest import BOILER

async def test_startup_gate_does_not_confuse_missing_mqtt_with_runtime_failure(rig):
    await rig.enabled()
    rig.room()
    await rig.settle()
    deadline = rig.hass.states.get('input_datetime.heating_boiler_deadline').attributes['timestamp']
    await rig.hass.services.async_call('input_boolean', 'turn_off',
        {'entity_id':'input_boolean.heating_controller_ready'}, blocking=True)
    rig.state(BOILER, 'unavailable')
    await rig.settle()
    assert rig.hass.states.is_state('input_boolean.heating_safety_lock', 'off')
    rig.state(BOILER, 'on')
    await rig.hass.services.async_call('input_boolean', 'turn_on',
        {'entity_id':'input_boolean.heating_controller_ready'}, blocking=True)
    await rig.settle()
    assert rig.hass.states.get('input_datetime.heating_boiler_deadline').attributes['timestamp'] == deadline
    assert rig.hass.states.is_state(BOILER, 'on')

async def test_lock_cannot_be_acknowledged_with_relay_on(rig):
    await rig.enabled()
    rig.room()
    await rig.settle()
    deadline = rig.hass.states.get('input_datetime.heating_boiler_deadline').attributes['timestamp']
    await rig.hass.services.async_call('script', 'heating_reset_safety', {}, blocking=True)
    assert rig.hass.states.get('input_datetime.heating_boiler_deadline').attributes['timestamp'] == deadline

async def test_confirmed_off_allows_safety_reset(rig):
    await rig.hass.services.async_call('input_boolean', 'turn_on',
        {'entity_id':'input_boolean.heating_safety_lock'}, blocking=True)
    await rig.hass.services.async_call('script', 'heating_reset_safety', {}, blocking=True)
    assert rig.hass.states.is_state('input_boolean.heating_safety_lock', 'off')

async def test_floor_requires_active_mode_and_open_emitter(rig):
    await rig.enabled()
    rig.state('sensor.living_room_temperature_sensor_temperature', '18')
    rig.state('climate.living_room_floor_heating', 'off')
    rig.state('switch.floor_heating_controller_l1', 'on')
    await rig.settle()
    assert rig.hass.states.is_state(BOILER, 'off')
    rig.state('climate.living_room_floor_heating', 'heat')
    await rig.settle()
    assert rig.hass.states.is_state(BOILER, 'on')
    rig.state('binary_sensor.kitchen_window_sensor_contact', 'unknown')
    await rig.settle()
    assert rig.hass.states.is_state(BOILER, 'off')
