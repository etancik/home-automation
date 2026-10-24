from pathlib import Path
from datetime import timedelta

import pytest
import yaml
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

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


@pytest.mark.parametrize('sun,kelvin,brightness', [('above_horizon', 4000, 100), ('below_horizon', 2237, 50)])
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


async def test_switch_on_updates_only_that_zone(hass, profiles):
    hass.states.async_set('light.kitchen_table_light', 'on')
    await hass.async_block_till_done()
    assert profiles == [{'entity_id': ['light.kitchen_table_light'], 'color_temp_kelvin': 2237,
                         'brightness_pct': 50, 'transition': 1}]


@pytest.mark.parametrize('first,late', [(PALM, FIREPLACE), (FIREPLACE, PALM)])
async def test_late_member_receives_day_profile_after_group_is_already_on(hass, profiles, first, late):
    hass.states.async_set(FIREPLACE, 'off')
    hass.states.async_set(PALM, 'off')
    hass.states.async_set(FRONT, 'off', {'entity_id': [FIREPLACE, PALM]})
    hass.states.async_set('sun.sun', 'above_horizon')
    await hass.async_block_till_done()
    profiles.clear()
    hass.states.async_set(first, 'on')
    hass.states.async_set(FRONT, 'on', {'entity_id': [FIREPLACE, PALM]})
    await hass.async_block_till_done()
    assert profiles
    assert all(call['entity_id'] == [first] for call in profiles)
    profiles.clear()
    # The group remains on; the second bulb reports its state later.
    hass.states.async_set(late, 'on', {'brightness': 51, 'color_temp_kelvin': 2237})
    await hass.async_block_till_done()
    assert profiles
    assert any(late in call['entity_id'] for call in profiles)
    assert all(call['color_temp_kelvin'] == 4000 and call['brightness_pct'] == 100 for call in profiles)


@pytest.mark.parametrize('guard', [MANUAL, 'input_boolean.cinema_active', 'input_boolean.cinema_applying'])
async def test_member_switch_on_respects_manual_and_cinema(hass, profiles, guard):
    hass.states.async_set(guard, 'on')
    hass.states.async_set(PALM, 'on')
    await hass.async_block_till_done()
    assert profiles == []


async def test_rear_member_switch_on_refreshes_only_rear(hass, profiles):
    rear = 'light.living_room_bookshelf_light'
    hass.states.async_set(rear, 'off')
    hass.states.async_set('light.living_room_rear', 'on', {'entity_id': [rear]})
    await hass.async_block_till_done()
    profiles.clear()
    hass.states.async_set(rear, 'on')
    await hass.async_block_till_done()
    assert profiles == [{'entity_id': [rear], 'color_temp_kelvin': 2237,
                         'brightness_pct': 50, 'transition': 1}]


async def test_sun_transition_updates_lit_zones(hass, profiles):
    hass.states.async_set('sun.sun', 'above_horizon')
    await hass.async_block_till_done()
    assert profiles == [{'entity_id': [FIREPLACE], 'color_temp_kelvin': 4000,
                         'brightness_pct': 100, 'transition': 1}]


async def test_manual_brightness_is_not_reapplied_on_five_minute_tick(hass, profiles):
    hass.states.async_set(FIREPLACE, 'on', {'brightness': 25})
    await hass.async_block_till_done()
    now = dt_util.utcnow().replace(second=0, microsecond=0)
    for minute in range(1, 11):
        async_fire_time_changed(hass, now + timedelta(minutes=minute))
        await hass.async_block_till_done()
    assert profiles == []


@pytest.mark.parametrize('guard', ['cinema_active', 'cinema_applying'])
async def test_cinema_blocks_living_room_time_profiles(hass, profiles, guard):
    hass.states.async_set('input_boolean.' + guard, 'on')
    hass.states.async_set('sun.sun', 'above_horizon')
    await hass.async_block_till_done()
    assert profiles == []
