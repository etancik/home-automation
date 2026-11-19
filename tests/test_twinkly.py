from pathlib import Path
from datetime import timedelta

import pytest
import yaml
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

PACKAGE = Path(__file__).resolve().parents[1] / 'homeassistant/locations/house/packages/lighting_twinkly.yaml'
LIGHT = 'light.home_stairs'
MODE = 'select.home_stairs_mode'
GUARD = 'automation.twinkly_stairs_night_guard'


@pytest.fixture
async def twinkly(hass, freezer):
    freezer.move_to(dt_util.utcnow().replace(minute=1, second=0, microsecond=0))
    calls = []

    async def light(call):
        calls.append(('light', dict(call.data)))
        hass.states.async_set(LIGHT, 'on', {'brightness': call.data['brightness']})

    async def mode(call):
        calls.append(('select', dict(call.data)))
        hass.states.async_set(MODE, call.data['option'])

    hass.services.async_register('light', 'turn_on', light)
    hass.services.async_register('select', 'select_option', mode)
    hass.states.async_set('sun.sun', 'below_horizon')
    hass.states.async_set(LIGHT, 'on', {'brightness': 180})
    hass.states.async_set(MODE, 'demo')
    config = yaml.safe_load(PACKAGE.read_text())
    assert await async_setup_component(hass, 'automation', {'automation': config['automation']})
    await hass.async_block_till_done()
    yield calls
    await hass.services.async_call('automation', 'turn_off', {
        'entity_id': [s.entity_id for s in hass.states.async_all('automation')],
        'stop_actions': True,
    }, blocking=True)


async def tick(hass, freezer, minute=5):
    now = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
    freezer.move_to(now + timedelta(minutes=minute))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()


async def test_button_changes_survive_until_five_minute_check(hass, twinkly, freezer):
    hass.states.async_set(MODE, 'movie')
    await hass.async_block_till_done()
    assert twinkly == []
    await tick(hass, freezer, 4)
    assert twinkly == []
    await tick(hass, freezer)
    assert twinkly == [
        ('light', {'entity_id': [LIGHT], 'brightness': 8}),
        ('select', {'entity_id': [MODE], 'option': 'color'}),
    ]
    twinkly.clear()
    await tick(hass, freezer, 10)
    assert twinkly == []


@pytest.mark.parametrize('sun,light,mode,brightness', [
    ('above_horizon', 'on', 'demo', 180),
    ('below_horizon', 'off', 'demo', 180),
    ('below_horizon', 'on', 'off', 180),
    ('below_horizon', 'unavailable', 'demo', 180),
    ('below_horizon', 'on', 'unavailable', 180),
    ('below_horizon', 'on', 'unknown', 180),
    ('unknown', 'on', 'demo', 180),
    ('below_horizon', 'on', 'color', None),
])
async def test_day_off_and_unavailable_are_left_alone(hass, twinkly, freezer, sun, light, mode, brightness):
    hass.states.async_set('sun.sun', sun)
    hass.states.async_set(LIGHT, light, {'brightness': brightness})
    hass.states.async_set(MODE, mode)
    await hass.async_block_till_done()
    await tick(hass, freezer)
    assert twinkly == []


@pytest.mark.parametrize('mode,brightness,expected', [
    ('demo', 8, [('select', {'entity_id': [MODE], 'option': 'color'})]),
    ('color', 100, [('light', {'entity_id': [LIGHT], 'brightness': 8})]),
    ('color', 8, []),
])
async def test_only_deviations_are_corrected(hass, twinkly, freezer, mode, brightness, expected):
    hass.states.async_set(MODE, mode)
    hass.states.async_set(LIGHT, 'on', {'brightness': brightness})
    await hass.async_block_till_done()
    await tick(hass, freezer)
    assert twinkly == expected


async def test_reconnected_light_is_repaired_on_next_tick(hass, twinkly, freezer):
    hass.states.async_set(LIGHT, 'unavailable')
    await hass.async_block_till_done()
    await tick(hass, freezer)
    assert twinkly == []
    hass.states.async_set(LIGHT, 'on', {'brightness': 255})
    await hass.async_block_till_done()
    assert twinkly == []
    await tick(hass, freezer, 10)
    assert hass.states.get(MODE).state == 'color'
    assert hass.states.get(LIGHT).attributes['brightness'] == 8


async def test_startup_restores_active_night_light(hass, twinkly):
    await hass.async_start()
    await hass.async_block_till_done()
    assert hass.states.get(MODE).state == 'color'
    assert hass.states.get(LIGHT).attributes['brightness'] == 8
    await hass.async_stop(force=True)
