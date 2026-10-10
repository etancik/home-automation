import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from homeassistant.components.mqtt.models import ReceiveMessage
from homeassistant.components.mqtt.trigger import TRIGGER_SCHEMA, async_attach_trigger
from homeassistant.helpers.script import Script
from homeassistant.helpers import config_validation as cv
from homeassistant.setup import async_setup_component


PACKAGE = Path(__file__).resolve().parents[1] / 'homeassistant/locations/house/packages/lighting_living_room.yaml'


@pytest.fixture
async def buttons(hass, request):
    config = yaml.safe_load(PACKAGE.read_text())
    calls, listeners = [], []
    assert await async_setup_component(hass, 'input_boolean', {'input_boolean': config['input_boolean']})

    async def record(call):
        calls.append((call.domain, call.service, call.data['entity_id']))

    for domain in ('light', 'switch'):
        for service in ('toggle', 'turn_on', 'turn_off'):
            hass.services.async_register(domain, service, record)

    automation = config['automation'][getattr(request, 'param', 0)]
    script = Script(hass, cv.SCRIPT_SCHEMA(automation.get('conditions', []) + automation['actions']), 'Button test', 'automation')

    async def action(variables, context=None):
        await script.async_run(variables, context)

    def subscribe(hass, topic, listener, **kwargs):
        listeners.append((topic, listener))
        return lambda: None

    with patch('homeassistant.components.mqtt.trigger.async_subscribe_internal', side_effect=subscribe):
        for item in automation['triggers']:
            trigger = TRIGGER_SCHEMA({'platform': item['trigger'], **{k: v for k, v in item.items() if k != 'trigger'}})
            await async_attach_trigger(hass, trigger, action, {'trigger_data': {'id': item.get('id', 'table'), 'idx': '0'}})

    async def send(payload, topic='zigbee2mqtt/Living Room Window Switch'):
        message = ReceiveMessage(topic=topic, subscribed_topic=topic, payload=json.dumps(payload), qos=0, retain=False, timestamp=datetime.now(timezone.utc))
        for subscribed_topic, listener in listeners:
            if subscribed_topic == topic:
                listener(message)
        await hass.async_block_till_done()

    return calls, send


async def test_disabled_buttons_do_nothing(hass, buttons):
    calls, send = buttons
    await send({'action': 'toggle_l1'})
    await send({'action': 'toggle_l2'})
    assert calls == []


async def test_each_press_toggles_only_its_group_and_ignores_release(hass, buttons):
    calls, send = buttons
    await hass.services.async_call('input_boolean', 'turn_on', {'entity_id': 'input_boolean.living_room_button_test_enabled'}, blocking=True)
    await send({'action': 'toggle_l1'})
    await send({'action': ''})
    await send({'state_l1': 'ON', 'state_l2': 'OFF'})
    await send({'action': 'release'})
    await send({'action': 'toggle_l1'})
    await send({'action': 'toggle_l2'})
    assert calls == [
        ('light', 'toggle', ['light.living_room_front']),
        ('light', 'toggle', ['light.living_room_front']),
        ('light', 'toggle', ['light.living_room_rear']),
    ]


@pytest.mark.parametrize('buttons,topic,presses,targets', [
    (1, 'zigbee2mqtt/Living Room Passage Switch', ['toggle_l1', 'toggle_l2'],
     ['light.living_room_front', 'light.living_room_rear']),
    (2, 'zigbee2mqtt/Kitchen Table Switch', ['toggle'], ['light.kitchen_table_light']),
], indirect=['buttons'])
async def test_neutral_d_buttons_only_toggle_their_lights(buttons, topic, presses, targets):
    calls, send = buttons
    for press in presses:
        await send({'action': press}, topic)
    await send({'action': 'release'}, topic)
    await send({'state': 'ON', 'state_l1': 'ON'}, topic)
    await send({'action': presses[0]}, 'zigbee2mqtt/Unrelated Switch')
    assert calls == [('light', 'toggle', [entity]) for entity in targets]
