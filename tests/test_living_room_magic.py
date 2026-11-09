import asyncio
from datetime import timedelta
from pathlib import Path

import pytest
import yaml
from freezegun import freeze_time
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.script import Script
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed


PACKAGE = Path(__file__).resolve().parents[1] / 'homeassistant/locations/house/packages/lighting_living_room_magic.yaml'
LIGHTS = [f'light.living_room_{name}' for name in ['fireplace_light', 'palm_light', 'bookshelf_light', 'lamp']]
ROUND = 'script.living_room_magic_round'
LAST_ROUND = 'input_text.living_room_magic_last_round'
SIGNAL = 'input_select.living_room_magic_signal'


@pytest.fixture
async def magic(hass, request):
    config = yaml.safe_load(PACKAGE.read_text(encoding='utf-8'))
    if getattr(request, 'param', None) == 'firefly':
        for action in config['script']['living_room_magic_round']['sequence']:
            if 'round_name' in action.get('variables', {}):
                action['variables']['round_name'] = 'firefly'
    calls = []

    async def record(call):
        calls.append((call.domain, call.service, dict(call.data)))

    for domain, services in [('light', ['turn_on']), ('scene', ['create', 'turn_on', 'delete'])]:
        for service in services:
            hass.services.async_register(domain, service, record)
    for entity in LIGHTS:
        hass.states.async_set(entity, 'off')
    for entity in ['script.cinema_lighting', 'input_boolean.cinema_active', 'input_boolean.cinema_applying']:
        hass.states.async_set(entity, 'off')
    for domain in ['input_select', 'input_text', 'script']:
        assert await async_setup_component(hass, domain, {domain: config[domain]})
    button = Script(hass, cv.SCRIPT_SCHEMA(config['automation'][0]['actions']), 'Magic button test', 'automation')

    async def press():
        await button.async_run()
        await settle()

    async def advance(seconds):
        freezer.tick(timedelta(seconds=seconds))
        async_fire_time_changed(hass, dt_util.utcnow())
        await settle()

    await hass.async_start()
    with freeze_time(real_asyncio=True) as freezer:
        yield calls, press, advance
        await hass.services.async_call('script', 'turn_off', {'entity_id': ROUND}, blocking=True)


async def settle():
    # Let the in-memory services and templates run while the round waits for its next signal.
    for _ in range(30):
        await asyncio.sleep(0)


async def test_magic_restores_each_light_on_second_press(hass, magic):
    calls, press, advance = magic
    await press()
    assert calls[0] == ('scene', 'create', {
        'scene_id': 'living_room_magic_before', 'snapshot_entities': LIGHTS,
    })
    assert [data['entity_id'] for domain, _, data in calls if domain == 'light'] == [[light] for light in LIGHTS]
    await press()
    assert ('scene', 'turn_on', {'entity_id': ['scene.living_room_magic_before'], 'transition': 1}) in calls
    await advance(2)
    assert hass.states.get(ROUND).state == 'off'
    assert calls[-1][:2] == ('scene', 'delete')
    previous = hass.states.get(LAST_ROUND).state
    await press()
    assert hass.states.get(LAST_ROUND).state != previous


async def test_magic_finishes_after_four_frames(hass, magic):
    calls, press, advance = magic
    await press()
    for _ in range(4):
        await advance(4)
    assert len([call for call in calls if call[0] == 'light']) == 16
    assert calls[-1][:2] == ('scene', 'turn_on')
    await advance(2)
    assert hass.states.get(ROUND).state == 'off'


@pytest.mark.parametrize('magic', ['firefly'], indirect=True)
async def test_firefly_rewards_press_in_lamp_window(magic):
    calls, press, advance = magic
    await press()
    for _ in range(3):
        await advance(4)
    await press()
    assert calls[-1] == ('light', 'turn_on', {
        'entity_id': LIGHTS, 'hs_color': [43, 85], 'brightness_pct': 55, 'transition': 1,
    })
    await advance(2)
    assert calls[-1][:2] == ('scene', 'turn_on')


async def test_magic_cancels_for_other_controls_and_blocks_during_cinema(hass, magic):
    calls, press, advance = magic
    await press()
    hass.states.async_set('script.cinema_lighting', 'on')
    await hass.services.async_call('script', 'turn_on', {'entity_id': 'script.living_room_magic_cancel'}, blocking=True)
    await settle()
    assert hass.states.get(SIGNAL).state == 'cancel'
    assert calls[-1][:2] == ('scene', 'turn_on')
    await advance(2)
    assert hass.states.get(ROUND).state == 'off'
    calls.clear()
    await press()
    assert calls == []
