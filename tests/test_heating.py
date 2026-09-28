import datetime as dt
import pytest
import yaml
from homeassistant.helpers.template import Template
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed
from conftest import ROOT, BOILER, package

async def advance(rig, freezer, seconds):
    point = dt_util.utcnow() + dt.timedelta(seconds=seconds)
    freezer.move_to(point)
    async_fire_time_changed(rig.hass, point)
    await rig.settle()

async def test_legacy_disabled_zone_reproduced(rig):
    before=yaml.safe_load((ROOT/'tests/fixtures/heating_before.yaml').read_text())
    a=next(a for a in before if a['id']=='boiler_heating_control')
    variables=next(step['variables'] for step in a['actions'] if 'variables' in step)
    on=next(step for step in a['actions'] if 'if' in step and step['if'][0].get('state')=='off')
    rig.room(mode='off', action='idle')
    await rig.settle()
    assert Template(on['if'][1]['value_template'],rig.hass).async_render(variables) is True

async def test_disabled_zone_cannot_start(rig):
    await rig.enabled()
    rig.room(mode='off',action='idle')
    await rig.settle()
    assert rig.hass.states.is_state(BOILER,'off')
    assert not rig.calls

async def test_start_continue_stop_hysteresis(rig):
    await rig.enabled()
    rig.room(temp=20.5)
    await rig.settle()
    assert not rig.calls
    rig.room(temp=19.9)
    await rig.settle()
    assert rig.hass.states.is_state(BOILER,'on')
    rig.room(temp=20.8)
    await rig.settle()
    assert rig.hass.states.is_state(BOILER,'on')
    rig.room(temp=21,action='idle')
    await rig.settle()
    assert rig.calls==[(BOILER,'on'),(BOILER,'off')]

async def test_summer_disable_stops_and_blocks(rig):
    await rig.enabled()
    rig.room()
    await rig.settle()
    await rig.enabled(False)
    assert rig.hass.states.is_state(BOILER,'off')
    rig.room(temp=17)
    await rig.settle()
    assert rig.hass.states.is_state(BOILER,'off')

@pytest.mark.parametrize('value',['unknown','unavailable','bad-data'])
async def test_invalid_temperature_stops_lone_demand(rig,value):
    await rig.enabled()
    rig.room()
    await rig.settle()
    rig.state('sensor.bedroom_temperature_sensor_temperature',value)
    await rig.settle()
    assert rig.hass.states.is_state(BOILER,'off')

@pytest.mark.parametrize('value',['on','unavailable','unknown'])
async def test_open_or_unknown_contact_blocks_start(rig,value):
    await rig.enabled()
    rig.state('binary_sensor.bedroom_window_sensor_contact',value)
    rig.room()
    await rig.settle()
    assert not rig.calls

async def test_watchdog_latches_without_restart(rig,freezer):
    await rig.enabled()
    rig.room()
    await rig.settle()
    await advance(rig,freezer,4*3600+1)
    assert rig.hass.states.is_state(BOILER,'off')
    assert rig.hass.states.is_state('input_boolean.heating_safety_lock','on')
    rig.room(temp=17)
    await rig.settle()
    assert rig.calls==[(BOILER,'on'),(BOILER,'off')]

async def test_restart_reconciliation_preserves_deadline(rig,freezer):
    await rig.enabled()
    rig.room()
    await rig.settle()
    deadline=rig.hass.states.get('input_datetime.heating_boiler_deadline').attributes['timestamp']
    await advance(rig,freezer,3600)
    # Simulate boot reconciliation with restored persistent helper and relay state.
    await rig.hass.services.async_call('automation','trigger',
        {'entity_id':'automation.boiler_heating_control','skip_condition':False},blocking=True)
    assert rig.hass.states.get('input_datetime.heating_boiler_deadline').attributes['timestamp']==deadline
    await advance(rig,freezer,3*3600+1)
    assert rig.hass.states.is_state('input_boolean.heating_safety_lock','on')

async def test_running_boiler_without_deadline_locks(rig):
    await rig.enabled()
    rig.room()
    # Force unknown runtime as if restored from old config/manual relay override.
    await rig.hass.services.async_call('input_datetime','set_datetime',
        {'entity_id':'input_datetime.heating_boiler_deadline','timestamp':0},blocking=True)
    rig.state(BOILER,'on')
    await rig.settle()
    assert rig.hass.states.is_state('input_boolean.heating_safety_lock','on')
    assert rig.hass.states.is_state(BOILER,'off')

async def test_relay_command_failure_latches(rig):
    rig.failed.add('on')
    await rig.enabled()
    rig.room()
    await rig.settle()
    # Use the real five-second acknowledgement timeout (no frozen asyncio clock).
    assert rig.hass.states.is_state('input_boolean.heating_safety_lock','on')
    assert rig.hass.states.is_state(BOILER,'off')

async def test_relay_disconnect_during_run_latches(rig):
    await rig.enabled()
    rig.room()
    await rig.settle()
    rig.state(BOILER,'unavailable')
    await rig.settle()
    assert rig.hass.states.is_state('input_boolean.heating_safety_lock','on')
    rig.state(BOILER,'on')
    await rig.settle()
    assert rig.hass.states.is_state(BOILER,'off')

@pytest.mark.parametrize('initial',['off','heat','auto'])
async def test_window_restores_user_mode(rig,initial):
    rig.room(mode=initial)
    await rig.settle()
    rig.state('binary_sensor.bedroom_window_sensor_contact','on')
    await rig.settle()
    assert rig.hass.states.is_state('climate.bedroom_radiator_heat_valve','off')
    rig.state('binary_sensor.bedroom_window_sensor_contact','off')
    await rig.settle()
    assert rig.hass.states.is_state('climate.bedroom_radiator_heat_valve',initial)
