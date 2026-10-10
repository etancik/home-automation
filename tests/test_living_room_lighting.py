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


PACKAGE = Path(__file__).resolve().parents[1] / 'homeassistant/locations/house/packages/lighting_living_room.yaml'


@pytest.fixture
async def buttons(hass, request):
    config = yaml.safe_load(PACKAGE.read_text())
    calls, listeners = [], []

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

    async def send(payload, topic):
        message = ReceiveMessage(topic=topic, subscribed_topic=topic, payload=json.dumps(payload), qos=0, retain=False, timestamp=datetime.now(timezone.utc))
        for subscribed_topic, listener in listeners:
            if subscribed_topic == topic:
                listener(message)
        await hass.async_block_till_done()

    return calls, send


@pytest.mark.parametrize('buttons,topic,presses,targets', [
    (0, 'zigbee2mqtt/Living Room Passage Switch', ['toggle_l1', 'toggle_l2'],
     ['light.living_room_front', 'light.living_room_rear']),
    (1, 'zigbee2mqtt/Kitchen Table Switch', ['toggle'], ['light.kitchen_table_light']),
    (2, 'zigbee2mqtt/Kitchen Counter Switch', ['toggle'], ['light.kitchen_counter_light']),
], indirect=['buttons'])
async def test_neutral_d_buttons_only_toggle_their_lights(buttons, topic, presses, targets):
    calls, send = buttons
    for press in presses:
        await send({'action': press}, topic)
    await send({'action': 'release'}, topic)
    await send({'state': 'ON', 'state_l1': 'ON'}, topic)
    await send({'action': presses[0]}, 'zigbee2mqtt/Unrelated Switch')
    assert calls == [('light', 'toggle', [entity]) for entity in targets]
