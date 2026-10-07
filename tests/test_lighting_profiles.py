from pathlib import Path

import pytest
import yaml
from homeassistant.setup import async_setup_component

PACKAGE = Path(__file__).resolve().parents[1] / 'homeassistant/locations/house/packages/lighting_profiles.yaml'
FRONT = 'light.living_room_front'
FIREPLACE = 'light.living_room_fireplace_light'
PALM = 'light.living_room_palm_light'
MANUAL = 'input_boolean.lighting_manual_living_room_front'


@pytest.fixture
async def profiles(hass):
    config = yaml.safe_load(PACKAGE.read_text())
    calls = []

    async def record(call):
        calls.append(dict(call.data))

    hass.services.async_register('light', 'turn_on', record)
    hass.states.async_set(FIREPLACE, 'on')
    hass.states.async_set(PALM, 'off')
    hass.states.async_set(FRONT, 'on', {'entity_id': [FIREPLACE, PALM]})
    for entity in ('light.living_room_rear', 'light.kitchen_counter_light', 'light.kitchen_table_light'):
        hass.states.async_set(entity, 'off')
    hass.states.async_set('sun.sun', 'below_horizon')
    for domain in ('input_boolean', 'script', 'automation'):
        assert await async_setup_component(hass, domain, {domain: config[domain]})
    await hass.async_block_till_done()
    yield calls
    await hass.services.async_call('automation', 'turn_off', {
        'entity_id': [s.entity_id for s in hass.states.async_all('automation')],
        'stop_actions': True,
    }, blocking=True)


@pytest.mark.parametrize('sun,kelvin,brightness', [('above_horizon', 4000, 80), ('below_horizon', 2300, 45)])
async def test_refresh_uses_profile_without_turning_on_unlit_members(hass, profiles, sun, kelvin, brightness):
    hass.states.async_set('sun.sun', sun)
    await hass.async_block_till_done()
    profiles.clear()
    await hass.services.async_call('automation', 'trigger', {'entity_id': 'automation.lighting_refresh_time_profiles'}, blocking=True)
    await hass.async_block_till_done()
    assert profiles == [{'entity_id': [FIREPLACE], 'color_temp_kelvin': kelvin, 'brightness_pct': brightness, 'transition': 1}]


async def test_manual_mode_survives_refresh_and_resets_when_zone_off(hass, profiles):
    await hass.services.async_call('input_boolean', 'turn_on', {'entity_id': MANUAL}, blocking=True)
    await hass.services.async_call('automation', 'trigger', {'entity_id': 'automation.lighting_refresh_time_profiles'}, blocking=True)
    await hass.async_block_till_done()
    assert profiles == []
    hass.states.async_set(FRONT, 'off', {'entity_id': [FIREPLACE, PALM]})
    await hass.async_block_till_done()
    assert hass.states.get(MANUAL).state == 'off'


async def test_unavailable_or_off_zone_is_not_turned_on(hass, profiles):
    hass.states.async_set(FRONT, 'unavailable')
    await hass.async_block_till_done()
    await hass.services.async_call('automation', 'trigger', {'entity_id': 'automation.lighting_refresh_time_profiles'}, blocking=True)
    await hass.async_block_till_done()
    assert profiles == []
