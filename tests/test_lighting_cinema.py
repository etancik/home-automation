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
LAMP = 'light.living_room_lamp'
SHUTTER = 'cover.living_room_roller_shutter'
LAMP_SCENE = 'scene.cinema_before_lamp'
MAGIC_ROUND = 'script.living_room_magic_round'


@pytest.fixture
async def cinema(hass, freezer):
    freezer.move_to('2026-11-07T22:00:00Z')
    await hass.config.async_set_time_zone('Europe/Prague')
    config = yaml.safe_load(PACKAGE.read_text())
    living_room = yaml.safe_load(PACKAGE.with_name('lighting_living_room.yaml').read_text())
    config['automation'].extend(
        item for item in living_room['automation'] if item['id'] == 'living_room_lamp_schedule'
    )
    # Device settling delays are exercised by guards separately; avoid wall-clock sleeps.
    def skip_delays(actions):
        for action in actions:
            if 'delay' in action:
                action['delay'] = 0
            for branch in action.get('choose', []):
                skip_delays(branch['sequence'])
            for key in ['then', 'else']:
                skip_delays(action.get(key, []))

    skip_delays(config['script']['cinema_lighting']['sequence'])
    calls = []

    async def record(call):
        calls.append((call.domain, call.service, dict(call.data)))

    async def create_scene(call):
        await record(call)
        members = call.data.get('snapshot_entities') or list(call.data['entities'])
        hass.states.async_set('scene.' + call.data['scene_id'], 'unknown', {'entity_id': members})

    async def delete_scene(call):
        await record(call)
        for entity in call.data['entity_id']:
            hass.states.async_remove(entity)

    hass.services.async_register('scene', 'create', create_scene)
    hass.services.async_register('scene', 'delete', delete_scene)
    for domain, services in [('light', ['turn_on', 'turn_off']), ('scene', ['turn_on'])]:
        for service in services:
            hass.services.async_register(domain, service, record)
    hass.states.async_set(FIREPLACE, 'on', {'brightness': 150})
    hass.states.async_set(PALM, 'off')
    hass.states.async_set(BOOKSHELF, 'on', {'brightness': 150})
    hass.states.async_set(FRONT, 'on', {'entity_id': [FIREPLACE, PALM]})
    hass.states.async_set(REAR, 'on', {'entity_id': [BOOKSHELF]})
    for side in ['front', 'rear']:
        hass.states.async_set('input_boolean.lighting_manual_living_room_' + side, 'off')
    hass.states.async_set(PLAYER, 'idle', {'app_name': 'YouTube'})
    assert await async_setup_component(hass, 'input_boolean', {'input_boolean': config['input_boolean']})
    assert await async_setup_component(hass, 'script', {'script': config['script']})
    await hass.services.async_call('input_boolean', 'turn_on', {'entity_id': 'input_boolean.cinema_enabled'}, blocking=True)
    assert await async_setup_component(hass, 'automation', {'automation': config['automation']})
    await hass.async_start()
    await hass.async_block_till_done()
    yield calls
    await hass.services.async_call('automation', 'turn_off', {
        'entity_id': [s.entity_id for s in hass.states.async_all('automation')], 'stop_actions': True,
    }, blocking=True)
    await hass.async_stop(force=True)


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


async def test_cinema_readiness_check_leaves_active_magic_round_alone(hass, cinema):
    async def cancel(call):
        pytest.fail('Readiness check canceled the active magic round')

    hass.services.async_register('script', 'living_room_magic_cancel', cancel)
    hass.states.async_set(MAGIC_ROUND, 'on')
    hass.states.async_set(REAR, 'off', {'entity_id': [BOOKSHELF]})
    hass.states.async_set(REAR, 'on', {'entity_id': [BOOKSHELF]})
    await hass.async_block_till_done()
    await hass.services.async_call('script', 'cinema_lighting', {'intent': 'ready'}, blocking=True)
    assert cinema == []
    assert hass.states.get(MAGIC_ROUND).state == 'on'


async def test_video_playback_restores_magic_round_before_cinema_snapshot(hass, cinema):
    async def cancel(call):
        cinema.append(('script', 'living_room_magic_cancel', {}))
        hass.states.async_set(MAGIC_ROUND, 'off')

    hass.services.async_register('script', 'living_room_magic_cancel', cancel)
    hass.states.async_set(MAGIC_ROUND, 'on')
    await play(hass)
    assert [call[:2] for call in cinema[:2]] == [('script', 'living_room_magic_cancel'), ('scene', 'create')]
    assert hass.states.get('input_boolean.cinema_active').state == 'on'


@pytest.mark.parametrize('app', ['Spotify', 'Music', 'Podcasts'])
async def test_music_does_not_start_cinema(hass, cinema, app):
    await play(hass, app)
    assert light_calls(cinema) == []
    assert hass.states.get('input_boolean.cinema_active').state == 'off'


async def test_pause_waits_two_seconds_then_fades_and_resume_preserves_snapshot(hass, cinema):
    await play(hass)
    cinema.clear()
    hass.states.async_set(PLAYER, 'paused', {'app_name': 'YouTube'})
    await hass.async_block_till_done()
    assert light_calls(cinema) == []
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=1))
    await hass.async_block_till_done()
    assert light_calls(cinema) == []
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=3))
    await hass.async_block_till_done()
    assert light_calls(cinema) == [
        ('light', 'turn_on', {'entity_id': [FRONT], 'brightness_pct': 10, 'color_temp_kelvin': 2237, 'transition': 3}),
        ('light', 'turn_on', {'entity_id': [REAR], 'brightness_pct': 50, 'color_temp_kelvin': 2237, 'transition': 3}),
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
    assert light_calls(cinema) == []
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=1))
    await hass.async_block_till_done()
    assert light_calls(cinema) == []
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=3))
    await hass.async_block_till_done()
    assert len(light_calls(cinema)) == 1
    assert light_calls(cinema)[0][2]['entity_id'] == [expected]
    assert light_calls(cinema)[0][2]['transition'] == 3


async def test_start_waits_for_available_lights(hass, cinema):
    hass.states.async_set(REAR, 'unavailable', {'entity_id': [BOOKSHELF]})
    await hass.async_block_till_done()
    await play(hass)
    assert cinema == []
    hass.states.async_set(REAR, 'on', {'entity_id': [BOOKSHELF]})
    await hass.async_block_till_done()
    assert hass.states.get('input_boolean.cinema_active').state == 'on'


async def test_pause_shorter_than_two_seconds_does_not_brighten(hass, cinema):
    await play(hass)
    cinema.clear()
    hass.states.async_set(PLAYER, 'paused', {'app_name': 'YouTube'})
    await hass.async_block_till_done()
    assert light_calls(cinema) == []
    await play(hass)
    cinema.clear()
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=3))
    await hass.async_block_till_done()
    assert light_calls(cinema) == []


async def close_shutter(hass):
    hass.states.async_set(SHUTTER, 'closing')
    await hass.async_block_till_done()
    hass.states.async_set(SHUTTER, 'closed')
    await hass.async_block_till_done()


async def advance(hass, freezer, when):
    freezer.move_to(when)
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()


async def test_lamp_follows_shutter_and_local_cutoff(hass, cinema, freezer):
    hass.states.async_set(LAMP, 'off')
    hass.states.async_set(SHUTTER, 'closed')
    await hass.async_block_till_done()
    assert light_calls(cinema) == []
    await close_shutter(hass)
    assert light_calls(cinema) == [
        ('light', 'turn_on', {'entity_id': [LAMP], 'brightness_pct': 50, 'color_temp_kelvin': 2237}),
    ]
    cinema.clear()
    await advance(hass, freezer, '2026-11-07T23:59:59Z')
    assert light_calls(cinema) == []
    await advance(hass, freezer, '2026-11-08T00:00:01Z')
    assert light_calls(cinema) == [('light', 'turn_off', {'entity_id': [LAMP]})]


async def test_lamp_follows_front_lights_until_nightly_cutoff(hass, cinema, freezer):
    hass.states.async_set(LAMP, 'on', {'brightness': 255})
    await play(hass)
    assert light_calls(cinema)[0] == ('light', 'turn_off', {'entity_id': [FRONT, LAMP]})
    assert hass.states.get(LAMP_SCENE).attributes['entity_id'] == [LAMP]

    cinema.clear()
    hass.states.async_set(PLAYER, 'paused', {'app_name': 'YouTube'})
    await hass.async_block_till_done()
    await advance(hass, freezer, '2026-11-07T22:00:03Z')
    assert light_calls(cinema)[0] == (
        'light', 'turn_on', {'entity_id': [FRONT, LAMP], 'brightness_pct': 10,
                             'color_temp_kelvin': 2237, 'transition': 3},
    )

    cinema.clear()
    await advance(hass, freezer, '2026-11-08T00:00:01Z')
    assert light_calls(cinema) == [('light', 'turn_off', {'entity_id': [LAMP]})]
    assert hass.states.get(LAMP_SCENE) is None
    cinema.clear()
    await play(hass)
    hass.states.async_set(PLAYER, 'paused', {'app_name': 'YouTube'})
    await hass.async_block_till_done()
    await advance(hass, freezer, '2026-11-08T00:00:07Z')
    assert all(LAMP not in call[2]['entity_id'] for call in light_calls(cinema))
    await play(hass, 'Spotify')
    assert all(LAMP_SCENE not in call[2].get('entity_id', []) for call in cinema if call[0] == 'scene')


async def test_shutter_closing_during_playback_sets_lamp_restore_scene(hass, cinema):
    hass.states.async_set(LAMP, 'off')
    await play(hass)
    cinema.clear()
    await close_shutter(hass)
    assert light_calls(cinema) == []
    assert cinema == [('scene', 'create', {
        'scene_id': 'cinema_before_lamp',
        'entities': {LAMP: {'state': 'on', 'brightness': 128,
                            'color_mode': 'color_temp', 'color_temp_kelvin': 2237}},
    })]
    await play(hass, 'Spotify')
    assert ('scene', 'turn_on', {'entity_id': [LAMP_SCENE]}) in cinema
    assert hass.states.get(LAMP_SCENE) is None
