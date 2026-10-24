from datetime import timedelta
from pathlib import Path

import pytest
import yaml
from homeassistant.helpers.sun import get_astral_event_date
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

PACKAGES = Path(__file__).resolve().parents[1] / 'homeassistant/locations/house/packages'


@pytest.fixture
async def solar(hass, freezer):
    freezer.move_to('2026-10-24T00:00:00Z')
    await hass.config.async_set_time_zone('Europe/Prague')
    hass.config.latitude = 50
    hass.config.longitude = 14
    shading = yaml.safe_load((PACKAGES / 'shading_v1.yaml').read_text())
    lighting = yaml.safe_load((PACKAGES / 'lighting.yaml').read_text())
    calls = []

    async def record(call):
        calls.append((call.domain, call.service, dict(call.data)))

    for room in ['bedroom', 'kids_room', 'workshop', 'kitchen', 'living_room']:
        hass.states.async_set('cover.' + room + '_roller_shutter', 'open', {'current_position': 100})
        contact = room + ('_door' if room == 'living_room' else '_window')
        hass.states.async_set('binary_sensor.' + contact + '_sensor_contact', 'off')
    for domain, service in [('cover', 'set_cover_position'), ('cover', 'stop_cover'),
                            ('light', 'turn_on'), ('light', 'turn_off')]:
        hass.services.async_register(domain, service, record)
    assert await async_setup_component(hass, 'input_boolean', {'input_boolean': shading['input_boolean']})
    assert await async_setup_component(hass, 'script', {'script': shading['script']})
    assert await async_setup_component(hass, 'automation', {
        'automation': shading['automation'] + [lighting['automation'][1]]})
    await hass.services.async_call('input_boolean', 'turn_on',
        {'entity_id': 'input_boolean.shading_automation_enabled'}, blocking=True)
    await hass.async_start()
    await hass.async_block_till_done()
    calls.clear()
    yield calls
    await hass.services.async_call('automation', 'turn_off', {
        'entity_id': [s.entity_id for s in hass.states.async_all('automation')],
        'stop_actions': True}, blocking=True)
    await hass.async_stop(force=True)


async def advance(hass, freezer, when):
    freezer.move_to(when)
    async_fire_time_changed(hass, when)
    await hass.async_block_till_done()


async def test_kids_light_switches_off_with_morning_shutters(hass, solar, freezer):
    sunrise = get_astral_event_date(hass, 'sunrise', dt_util.now().date())
    await advance(hass, freezer, sunrise - timedelta(minutes=31))
    assert solar == []
    await advance(hass, freezer, sunrise - timedelta(minutes=30) + timedelta(seconds=1))
    lights = [call for call in solar if call[0] == 'light']
    covers = [call for call in solar if call[0] == 'cover']
    assert lights == [('light', 'turn_off', {'entity_id': ['light.kids_room_door_led_strip']})]
    assert {call[2]['entity_id'][0] for call in covers} == {
        'cover.' + room + '_roller_shutter' for room in ['kids_room', 'workshop', 'kitchen', 'living_room']}
    assert all(call[2]['position'] == 100 for call in covers)
    solar.clear()
    await advance(hass, freezer, sunrise + timedelta(seconds=1))
    assert solar == [('light', 'turn_off', {'entity_id': ['light.bedroom_led_strip']})]


async def test_shutters_close_early_and_follow_windows_before_sunset(hass, solar, freezer):
    sunset = get_astral_event_date(hass, 'sunset', dt_util.now().date())
    # Avoid replaying morning events while jumping to the afternoon.
    await advance(hass, freezer, sunset - timedelta(minutes=11))
    solar.clear()
    await advance(hass, freezer, sunset - timedelta(minutes=10) + timedelta(seconds=1))
    assert len(solar) == 5
    assert ('cover', 'set_cover_position', {'entity_id': ['cover.kids_room_roller_shutter'], 'position': 0}) in solar
    solar.clear()
    await advance(hass, freezer, sunset - timedelta(minutes=5))
    hass.states.async_set('binary_sensor.kids_room_window_sensor_contact', 'on')
    await hass.async_block_till_done()
    assert solar == [('cover', 'set_cover_position', {'entity_id': ['cover.kids_room_roller_shutter'], 'position': 20})]
