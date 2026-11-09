import asyncio
from datetime import timedelta
from pathlib import Path

import pytest
import yaml
from freezegun import freeze_time
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.script import Script
from homeassistant.helpers.template import Template
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed


PACKAGE = Path(__file__).resolve().parents[1] / 'homeassistant/locations/house/packages/lighting_living_room_magic.yaml'
LIGHTS = [f'light.living_room_{name}' for name in ['fireplace_light', 'palm_light', 'bookshelf_light', 'lamp']]
ROUND = 'script.living_room_magic_round'
CANCEL = 'input_boolean.living_room_magic_cancel_requested'


@pytest.fixture
async def magic(hass):
    config = yaml.safe_load(PACKAGE.read_text(encoding='utf-8'))
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
    for domain in ['input_boolean', 'input_button', 'script']:
        assert await async_setup_component(hass, domain, {domain: config[domain]})
    automation = config['automation'][0]
    trigger = automation['triggers'][0]
    payload = Template(trigger['value_template'], hass)
    button = Script(hass, cv.SCRIPT_SCHEMA(automation['actions']), 'Magic button test', 'automation')

    async def press(gesture='single'):
        freezer.tick(timedelta(milliseconds=20))
        if payload.async_render({'value_json': {'action': gesture}}) == trigger['payload']:
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
    for _ in range(50):
        await asyncio.sleep(0)


def light_frames(calls):
    return [data for domain, _, data in calls if domain == 'light']


async def test_magic_changes_whole_room_only_on_press_and_restores_on_idle(hass, magic):
    calls, press, advance = magic
    await press('double')
    assert calls[0] == ('scene', 'create', {
        'scene_id': 'living_room_magic_before', 'snapshot_entities': LIGHTS,
    })
    assert len(light_frames(calls)) == 1
    first_color = light_frames(calls)[0]
    assert first_color['entity_id'] == LIGHTS
    first_hue = first_color['hs_color'][0]
    await advance(2)
    await advance(3)
    assert light_frames(calls) == [first_color]
    await press()
    assert len(light_frames(calls)) == 2
    assert light_frames(calls)[1] == {**first_color, 'hs_color': [(first_hue + 72) % 360, 80]}
    await advance(2)
    await advance(4)
    assert len(light_frames(calls)) == 2
    assert calls[-1] == ('scene', 'turn_on', {'entity_id': ['scene.living_room_magic_before'], 'transition': 1})
    await advance(2)
    assert hass.states.get(ROUND).state == 'off'
    assert calls[-1][:2] == ('scene', 'delete')


async def test_rapid_taps_are_combined_into_one_color_change(hass, magic):
    calls, press, advance = magic
    await press()
    for gesture in ['single', 'double', 'double', 'single']:
        await press(gesture)
    assert len(light_frames(calls)) == 1
    await advance(2)
    assert len(light_frames(calls)) == 2
    await advance(2)
    assert hass.states.get(ROUND).state == 'on'
    assert len(light_frames(calls)) == 2
    assert len([call for call in calls if call[:2] == ('scene', 'create')]) == 1
    await advance(4)
    assert len(light_frames(calls)) == 2
    assert calls[-1][:2] == ('scene', 'turn_on')


async def test_magic_cancels_for_other_controls_and_blocks_during_cinema(hass, magic):
    calls, press, advance = magic
    await press('long')
    assert calls == []
    await press()
    hass.states.async_set('script.cinema_lighting', 'on')
    await hass.services.async_call('script', 'turn_on', {'entity_id': 'script.living_room_magic_cancel'}, blocking=True)
    await settle()
    assert hass.states.get(CANCEL).state == 'on'
    assert calls[-1][:2] == ('scene', 'turn_on')
    await advance(2)
    assert hass.states.get(ROUND).state == 'off'
    calls.clear()
    await press()
    assert calls == []
