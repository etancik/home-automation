import json
from pathlib import Path

import pytest
import yaml
from homeassistant.components.mqtt import MQTT_PUBLISH_SCHEMA
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.script import Script
from homeassistant.helpers.template import Template

PACKAGES = Path(__file__).resolve().parents[1] / 'homeassistant/locations/house/packages'


@pytest.fixture
def mqtt_calls(hass):
    calls = []

    async def publish(call):
        calls.append(dict(call.data))

    hass.services.async_register('mqtt', 'publish', publish, schema=MQTT_PUBLISH_SCHEMA)
    return calls


def automation_script(hass, package):
    config = yaml.safe_load((PACKAGES / package).read_text())['automation'][0]
    return Script(hass, cv.SCRIPT_SCHEMA(config.get('conditions', []) + config['actions']), 'MQTT contract', 'automation')


async def test_trv_reconcile_sends_valid_value_before_selecting_remote_sensor(hass, mqtt_calls):
    script = automation_script(hass, 'heating_sensor_sync.yaml')
    rooms = ('bedroom', 'downstairs_bathroom', 'kids_room', 'entrance', 'upstairs_bathroom', 'workshop')
    for i, room in enumerate(rooms):
        hass.states.async_set(f'sensor.{room}_temperature_sensor_temperature', str(19 + i / 10))
    await script.async_run({'trigger': {'id': 'reconcile'}})
    assert len(mqtt_calls) == 12
    for reading, mode in zip(mqtt_calls[::2], mqtt_calls[1::2]):
        assert reading['topic'] == mode['topic']
        value = json.loads(reading['payload'])['external_temperature_input']
        assert 0 <= value <= 99.9
        payload = json.loads(mode['payload'])
        assert payload['temperature_sensor_select'] == 'remote_temperature'
        assert -1 <= payload['temperature_accuracy'] <= -0.2
        assert 'system_mode' not in payload


@pytest.mark.parametrize('value', ['unavailable', 'unknown', '-1', '100', 'nan'])
async def test_bad_temperature_never_selects_remote_source(hass, mqtt_calls, value):
    hass.states.async_set('sensor.bedroom_temperature_sensor_temperature', value)
    await automation_script(hass, 'heating_sensor_sync.yaml').async_run({'trigger': {'id': 'reconcile'}})
    assert mqtt_calls == []


async def test_temperature_update_only_targets_changed_room(hass, mqtt_calls):
    for room in ('bedroom', 'kids_room'):
        hass.states.async_set(f'sensor.{room}_temperature_sensor_temperature', '21.5')
    await automation_script(hass, 'heating_sensor_sync.yaml').async_run({
        'trigger': {'id': '0', 'entity_id': 'sensor.kids_room_temperature_sensor_temperature'},
    })
    assert len(mqtt_calls) == 1
    assert mqtt_calls[0]['topic'] == 'zigbee2mqtt/Kids Room Radiator Heat Valve/set'
    assert json.loads(mqtt_calls[0]['payload']) == {'external_temperature_input': 21.5}


@pytest.mark.parametrize('abbreviated', [False, True])
async def test_goe_brightness_discovery_repair_preserves_id_and_does_not_loop(hass, mqtt_calls, abbreviated):
    dc, unit, uid = ('dev_cla', 'unit_of_meas', 'uniq_id') if abbreviated else ('device_class', 'unit_of_measurement', 'unique_id')
    original = {dc: 'illuminance', unit: '%', uid: 'go-e_917809_brightness_sensor', 'name': 'Brightness Sensor'}
    script = automation_script(hass, 'goe_charger.yaml')
    trigger = {'id': 'brightness', 'topic': 'homeassistant/sensor/go-e_917809/brightness_sensor/config', 'payload_json': original}
    await script.async_run({'trigger': trigger})
    assert len(mqtt_calls) == 1
    fixed = json.loads(mqtt_calls[0]['payload'])
    assert dc not in fixed
    assert fixed[unit] == '%'
    assert fixed[uid] == original[uid]
    assert mqtt_calls[0]['retain'] is True
    await script.async_run({'trigger': {**trigger, 'payload_json': fixed}})
    assert len(mqtt_calls) == 1


async def test_goe_no_error_is_text_and_repaired_discovery_does_not_loop(hass, mqtt_calls):
    original = {'name': 'Error State', 'val_tpl': "{{ ['None','FiAc'][value_json|int] }}", 'ops': ['None', 'FiAc'], 'uniq_id': 'go-e_600187_error_state'}
    script = automation_script(hass, 'goe_charger.yaml')
    trigger = {'id': 'error_state', 'topic': 'homeassistant/sensor/go-e_600187/error_state/config', 'payload_json': original}
    await script.async_run({'trigger': trigger})
    fixed = json.loads(mqtt_calls[0]['payload'])
    assert Template(fixed['val_tpl'], hass).async_render({'value_json': 0}) == 'NoError'
    assert Template(fixed['val_tpl'], hass).async_render({'value_json': 1}) == 'FiAc'
    assert fixed['ops'] == ['NoError', 'FiAc']
    assert fixed['uniq_id'] == original['uniq_id']
    await script.async_run({'trigger': {**trigger, 'payload_json': fixed}})
    assert len(mqtt_calls) == 1


async def test_goe_boolean_switch_repair_only_publishes_metadata(hass, mqtt_calls):
    original = {'name': 'Force Single Phase', 'uniq_id': 'go-e_600187_force_single_phase', 'stat_t': 'go-eCharger/600187/fsp', 'cmd_t': 'go-eCharger/600187/fsp/set'}
    script = automation_script(hass, 'goe_charger.yaml')
    trigger = {'id': 'single_phase', 'topic': 'homeassistant/switch/go-e_600187/force_single_phase/config', 'payload_json': original}
    await script.async_run({'trigger': trigger})
    fixed = json.loads(mqtt_calls[0]['payload'])
    assert fixed['payload_on'] == 'true' and fixed['payload_off'] == 'false'
    assert fixed['cmd_t'] == original['cmd_t']
    assert mqtt_calls[0]['topic'] == trigger['topic']
    await script.async_run({'trigger': {**trigger, 'payload_json': fixed}})
    assert len(mqtt_calls) == 1


async def test_empty_discovery_is_ignored(hass, mqtt_calls):
    await automation_script(hass, 'goe_charger.yaml').async_run({'trigger': {'id': 'brightness'}})
    assert mqtt_calls == []
