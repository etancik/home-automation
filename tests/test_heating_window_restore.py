import json
from datetime import timedelta

import pytest
from homeassistant.util import dt as dt_util

VALVE='climate.bedroom_radiator_heat_valve'
CONTACT='binary_sensor.bedroom_window_sensor_contact'
BLOCK='input_boolean.heating_window_bedroom'
BACKUP='input_text.heating_window_backup_bedroom'


def baseline(rig):
    return json.loads(rig.hass.states.get(BACKUP).state)


async def tick(rig):
    await rig.hass.services.async_call('automation','trigger',{
        'entity_id':'automation.heating_reconcile_window_blocks'},blocking=True)
    await rig.settle()


@pytest.fixture
async def delayed(rig):
    commands=[]

    async def command(call):
        commands.append((call.service,dict(call.data)))

    rig.hass.services.async_register('climate','set_hvac_mode',command)
    rig.hass.services.async_register('climate','set_temperature',command)
    return commands


async def acknowledge(rig, delayed, mode=None, temperature=None):
    if mode is not None:
        # Model distinct setpoints recalled by the physical TRV on mode changes.
        target={'off':7,'heat':18,'auto':19}[mode]
        rig.state(VALVE,mode,temperature=target,hvac_action='idle')
    if temperature is not None:
        rig.state(VALVE,rig.hass.states.get(VALVE).state,temperature=temperature)
    await rig.settle()


async def finish(rig, freezer):
    freezer.move_to(dt_util.utcnow()+timedelta(seconds=6))
    await tick(rig)
    assert rig.hass.states.is_state(BLOCK,'off')
    assert baseline(rig)=={}


async def test_reopen_before_heat_ack_preserves_original_mode_and_target(rig, delayed, freezer):
    rig.room(mode='heat',target=21)
    await rig.settle()
    rig.state(CONTACT,'on')
    await rig.settle()
    await acknowledge(rig,delayed,mode='off')
    rig.state(CONTACT,'off')
    await rig.settle()
    assert delayed[-1][1]['hvac_mode']=='heat'
    assert rig.hass.states.is_state(BLOCK,'on')
    rig.state(CONTACT,'on')
    await rig.settle()
    assert baseline(rig)['mode']=='heat'
    assert baseline(rig)['temperature']==21
    await acknowledge(rig,delayed,mode='heat')  # Late HEAT reply while window open.
    assert delayed[-1][1]['hvac_mode']=='off'
    await acknowledge(rig,delayed,mode='off')
    rig.state(CONTACT,'off')
    await rig.settle()
    await acknowledge(rig,delayed,mode='heat')
    assert delayed[-1][0]=='set_temperature'
    assert delayed[-1][1]['temperature']==21
    await acknowledge(rig,delayed,temperature=21)
    await finish(rig,freezer)
    assert rig.hass.states.is_state(VALVE,'heat')
    assert rig.hass.states.get(VALVE).attributes['temperature']==21


async def test_close_before_off_ack_cannot_prematurely_finish(rig, delayed, freezer):
    rig.room(mode='heat',target=21)
    await rig.settle()
    rig.state(CONTACT,'on')
    await rig.settle()
    rig.state(CONTACT,'off')
    await rig.settle()
    assert not baseline(rig)['off_confirmed']
    assert rig.hass.states.is_state(BLOCK,'on')
    assert delayed[-1][1]['hvac_mode']=='off'
    await acknowledge(rig,delayed,mode='off')
    assert delayed[-1][1]['hvac_mode']=='heat'
    await acknowledge(rig,delayed,mode='heat')
    await acknowledge(rig,delayed,temperature=21)
    await finish(rig,freezer)


@pytest.mark.parametrize('mode,target',[('heat',20.5),('auto',19.5),('off',7)])
async def test_restore_mode_specific_target_and_keep_intentionally_off(rig, delayed, freezer, mode,target):
    rig.room(mode=mode,target=target)
    await rig.settle()
    rig.state(CONTACT,'on')
    await rig.settle()
    await acknowledge(rig,delayed,mode='off')
    rig.state(CONTACT,'off')
    await rig.settle()
    if mode!='off':
        await acknowledge(rig,delayed,mode=mode)
        assert delayed[-1][1]['temperature']==target
        await acknowledge(rig,delayed,temperature=target)
    else:
        assert not delayed
    await finish(rig,freezer)
    assert rig.hass.states.is_state(VALVE,mode)


async def test_restored_backup_recovers_after_restart_and_unavailable_valve(rig, delayed, freezer):
    await rig.hass.services.async_call('input_text','set_value',{
        'entity_id':BACKUP,'value':json.dumps({'mode':'auto','temperature':19.5,'off_confirmed':True,'restored_since':0})},blocking=True)
    await rig.hass.services.async_call('input_boolean','turn_on',{'entity_id':BLOCK},blocking=True)
    rig.state(VALVE,'unavailable')
    await tick(rig)
    assert baseline(rig)['temperature']==19.5
    assert not delayed
    await acknowledge(rig,delayed,mode='off')
    assert delayed[-1][1]['hvac_mode']=='auto'
    await acknowledge(rig,delayed,mode='auto')
    await acknowledge(rig,delayed,temperature=19.5)
    await finish(rig,freezer)


async def test_unknown_contact_never_restores_heating(rig, delayed):
    rig.room(mode='heat',target=21)
    await rig.settle()
    rig.state(CONTACT,'unknown')
    await rig.settle()
    await acknowledge(rig,delayed,mode='off')
    await tick(rig)
    assert baseline(rig)['mode']=='heat'
    assert all(data.get('hvac_mode','off')=='off' for _,data in delayed)
    assert rig.hass.states.is_state(BLOCK,'on')


async def test_old_mode_only_block_does_not_invent_target(rig, delayed, freezer):
    rig.state(VALVE,'off',temperature=7)
    await rig.hass.services.async_call('input_select','select_option',{
        'entity_id':'input_select.heating_saved_bedroom','option':'heat'},blocking=True)
    await rig.hass.services.async_call('input_boolean','turn_on',{'entity_id':BLOCK},blocking=True)
    await tick(rig)
    assert baseline(rig)['temperature'] is None
    await acknowledge(rig,delayed,mode='heat')
    assert not any(service=='set_temperature' for service,_ in delayed)
    await finish(rig,freezer)


async def test_late_off_reply_during_confirmation_is_recovered(rig, delayed, freezer):
    rig.room(mode='heat',target=21)
    await rig.settle()
    rig.state(CONTACT,'on')
    await rig.settle()
    await acknowledge(rig,delayed,mode='off')
    rig.state(CONTACT,'off')
    await rig.settle()
    await acknowledge(rig,delayed,mode='heat')
    await acknowledge(rig,delayed,temperature=21)
    assert baseline(rig)['restored_since']>0
    await acknowledge(rig,delayed,mode='off')
    assert baseline(rig)['temperature']==21
    assert baseline(rig)['restored_since']==0
    await acknowledge(rig,delayed,mode='heat')
    await acknowledge(rig,delayed,temperature=21)
    await finish(rig,freezer)


async def test_floor_waits_for_both_contacts_and_restores_target(rig,freezer):
    floor='climate.living_room_floor_heating'
    rig.state('binary_sensor.kitchen_window_sensor_contact','on')
    rig.state('binary_sensor.living_room_door_sensor_contact','on')
    await rig.settle()
    rig.state(floor,'off',temperature=7)
    rig.state('binary_sensor.kitchen_window_sensor_contact','off')
    await rig.settle()
    assert rig.hass.states.is_state(floor,'off')
    rig.state('binary_sensor.living_room_door_sensor_contact','off')
    await rig.settle()
    assert rig.hass.states.is_state(floor,'heat')
    assert rig.hass.states.get(floor).attributes['temperature']==21
    freezer.move_to(dt_util.utcnow()+timedelta(seconds=6))
    await tick(rig)
    assert rig.hass.states.is_state('input_boolean.heating_window_living_room','off')
