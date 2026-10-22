from pathlib import Path
from datetime import timedelta

import pytest
import yaml
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

PACKAGE = Path(__file__).resolve().parents[1] / 'homeassistant/locations/house/packages/lighting_cinema.yaml'
PLAYER = 'media_player.living_room_apple_tv'
FRONT = 'light.living_room_front'
REAR = 'light.living_room_rear'
FIREPLACE = 'light.living_room_fireplace_light'
PALM = 'light.living_room_palm_light'
BOOKSHELF = 'light.living_room_bookshelf_light'


@pytest.fixture
async def cinema(hass):
    config = yaml.safe_load(PACKAGE.read_text())
    # Device settling delays are exercised by guards separately; avoid wall-clock sleeps.
    for branch in config['script']['cinema_lighting']['sequence'][1]['choose']:
        for action in branch['sequence']:
            if 'delay' in action:
                action['delay'] = 0
    calls = []

    async def record(call):
        calls.append((call.domain, call.service, dict(call.data)))

    for domain, services in [('light', ['turn_on', 'turn_off']), ('scene', ['create', 'turn_on'])]:
        for service in services:
            hass.services.async_register(domain, service, record)
    hass.states.async_set(FIREPLACE, 'on', {'brightness': 150})
    hass.states.async_set(PALM, 'off')
    hass.states.async_set(BOOKSHELF, 'on', {'brightness': 150})
    hass.states.async_set(FRONT, 'on', {'entity_id': [FIREPLACE, PALM]})
    hass.states.async_set(REAR, 'on', {'entity_id': [BOOKSHELF]})
    for side in ['front', 'rear']:
        hass.states.async_set('input_boolean.lighting_manual_living_room_' + side, 'off')
        hass.states.async_set('scene.cinema_before_' + side, 'scening')
    hass.states.async_set(PLAYER, 'idle', {'app_name': 'YouTube'})
    assert await async_setup_component(hass, 'input_boolean', {'input_boolean': config['input_boolean']})
    assert await async_setup_component(hass, 'script', {'script': config['script']})
    await hass.services.async_call('input_boolean', 'turn_on', {'entity_id': 'input_boolean.cinema_enabled'}, blocking=True)
    assert await async_setup_component(hass, 'automation', {'automation': config['automation']})
    await hass.async_block_till_done()
    yield calls
    await hass.services.async_call('automation', 'turn_off', {
        'entity_id': [s.entity_id for s in hass.states.async_all('automation')], 'stop_actions': True,
    }, blocking=True)


async def play(hass, app='YouTube'):
    hass.states.async_set(PLAYER, 'playing', {'app_name': app})
    await hass.async_block_till_done()


def light_calls(calls):
    return [c for c in calls if c[0] == 'light']


async def test_play_starts_cinema_and_snapshots_each_zone(hass, cinema):
    await play(hass)
    assert hass.states.get('input_boolean.cinema_active').state == 'on'
    snapshots = [c[2] for c in cinema if c[:2] == ('scene', 'create')]
    assert snapshots == [
        {'scene_id': 'cinema_before_front', 'snapshot_entities': [FIREPLACE, PALM]},
        {'scene_id': 'cinema_before_rear', 'snapshot_entities': [BOOKSHELF]},
    ]
    assert light_calls(cinema) == [
        ('light', 'turn_off', {'entity_id': [FRONT]}),
        ('light', 'turn_on', {'entity_id': [REAR], 'brightness_pct': 10, 'color_temp_kelvin': 2237, 'transition': 1}),
    ]


@pytest.mark.parametrize('app', ['Spotify', 'Music', 'Podcasts'])
async def test_music_does_not_start_cinema(hass, cinema, app):
    await play(hass, app)
    assert light_calls(cinema) == []
    assert hass.states.get('input_boolean.cinema_active').state == 'off'


async def test_pause_immediately_fades_both_zones_and_resume_preserves_snapshot(hass, cinema):
    await play(hass)
    cinema.clear()
    hass.states.async_set(PLAYER, 'paused', {'app_name': 'YouTube'})
    await hass.async_block_till_done()
    assert light_calls(cinema) == [
        ('light', 'turn_on', {'entity_id': [FRONT], 'brightness_pct': 20, 'color_temp_kelvin': 2237, 'transition': 2}),
        ('light', 'turn_on', {'entity_id': [REAR], 'brightness_pct': 50, 'color_temp_kelvin': 2237, 'transition': 2}),
    ]
    assert not any(c[:2] == ('scene', 'create') for c in cinema)
    cinema.clear()
    await play(hass)
    assert not any(c[:2] == ('scene', 'create') for c in cinema)
    assert light_calls(cinema)[0] == ('light', 'turn_off', {'entity_id': [FRONT]})
    assert light_calls(cinema)[1][2]['brightness_pct'] == 10


async def test_external_change_protects_zone_from_resume_and_restore(hass, cinema):
    await play(hass)
    hass.states.async_set(BOOKSHELF, 'on', {'brightness': 90})
    await hass.async_block_till_done()
    assert hass.states.get('input_boolean.cinema_override_rear').state == 'on'
    cinema.clear()
    await hass.services.async_call('script', 'cinema_lighting', {'intent': 'play'}, blocking=True)
    assert not any(c[0] == 'light' and c[1] == 'turn_on' for c in cinema)
    cinema.clear()
    await hass.services.async_call('input_boolean', 'turn_off', {'entity_id': 'input_boolean.cinema_enabled'}, blocking=True)
    await hass.async_block_till_done()
    assert [c[2] for c in cinema if c[:2] == ('scene', 'turn_on')] == [{'entity_id': ['scene.cinema_before_front']}]
    assert hass.states.get('input_boolean.cinema_active').state == 'off'


async def test_sleep_restores_both_zones(hass, cinema):
    await play(hass)
    cinema.clear()
    hass.states.async_set(PLAYER, 'off')
    await hass.async_block_till_done()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=4))
    await hass.async_block_till_done()
    assert [c[2] for c in cinema if c[:2] == ('scene', 'turn_on')] == [
        {'entity_id': ['scene.cinema_before_front']}, {'entity_id': ['scene.cinema_before_rear']},
    ]
    assert hass.states.get('input_boolean.cinema_active').state == 'off'


async def test_connection_loss_keeps_lights_and_snapshot(hass, cinema):
    await play(hass)
    cinema.clear()
    hass.states.async_set(PLAYER, 'unavailable')
    await hass.async_block_till_done()
    assert cinema == []
    assert hass.states.get('input_boolean.cinema_active').state == 'on'


async def test_switching_to_spotify_ends_cinema(hass, cinema):
    await play(hass)
    cinema.clear()
    await play(hass, 'Spotify')
    assert hass.states.get('input_boolean.cinema_active').state == 'off'
    assert len([c for c in cinema if c[:2] == ('scene', 'turn_on')]) == 2


async def test_applying_guard_ignores_own_light_changes(hass, cinema):
    await play(hass)
    await hass.services.async_call('input_boolean', 'turn_on', {'entity_id': 'input_boolean.cinema_applying'}, blocking=True)
    hass.states.async_set(BOOKSHELF, 'on', {'brightness': 26})
    await hass.async_block_till_done()
    assert hass.states.get('input_boolean.cinema_override_rear').state == 'off'


async def test_disabled_cinema_does_not_start(hass, cinema):
    await hass.services.async_call('input_boolean', 'turn_off', {'entity_id': 'input_boolean.cinema_enabled'}, blocking=True)
    await play(hass)
    assert cinema == []


@pytest.mark.parametrize('side, entity, expected', [
    ('front', FIREPLACE, REAR),
    ('rear', BOOKSHELF, FRONT),
])
async def test_pause_respects_each_zone_override_independently(hass, cinema, side, entity, expected):
    await play(hass)
    hass.states.async_set(entity, 'on', {'brightness': 90})
    await hass.async_block_till_done()
    assert hass.states.get('input_boolean.cinema_override_' + side).state == 'on'
    cinema.clear()
    hass.states.async_set(PLAYER, 'paused', {'app_name': 'YouTube'})
    await hass.async_block_till_done()
    assert len(light_calls(cinema)) == 1
    assert light_calls(cinema)[0][2]['entity_id'] == [expected]
    assert light_calls(cinema)[0][2]['transition'] == 2


async def test_start_waits_for_available_lights(hass, cinema):
    hass.states.async_set(REAR, 'unavailable', {'entity_id': [BOOKSHELF]})
    await hass.async_block_till_done()
    await play(hass)
    assert cinema == []
    hass.states.async_set(REAR, 'on', {'entity_id': [BOOKSHELF]})
    await hass.async_block_till_done()
    assert hass.states.get('input_boolean.cinema_active').state == 'on'
