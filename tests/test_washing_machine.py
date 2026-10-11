from pathlib import Path

import pytest
import yaml
from homeassistant.setup import async_setup_component
from homeassistant.core import State
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import mock_restore_cache

PACKAGE = Path(__file__).resolve().parents[1] / 'homeassistant/locations/house/packages/washing_machine.yaml'
POWER = 'sensor.laundry_room_washing_machine_smart_plug_power'
RUNNING = 'input_boolean.washing_machine_running'
SENSOR = 'binary_sensor.washing_machine'


@pytest.fixture
async def washer(hass):
    config = yaml.safe_load(PACKAGE.read_text(encoding='utf-8-sig'))
    logs = []
    async def record(call):
        logs.append(call.data['message'])
    hass.services.async_register('logbook', 'log', record)
    hass.states.async_set(POWER, '0')
    for domain in ('input_boolean', 'input_number', 'template', 'automation'):
        assert await async_setup_component(hass, domain, {domain: config[domain]})
    await hass.async_block_till_done()
    yield logs
    await hass.services.async_call('automation', 'turn_off', {
        'entity_id': 'automation.washing_machine_status_logging', 'stop_actions': True,
    }, blocking=True)


async def reconcile(hass):
    await hass.services.async_call('automation', 'trigger', {
        'entity_id': 'automation.washing_machine_status_logging',
    }, blocking=True)
    await hass.async_block_till_done()


async def age(hass, name, seconds):
    await hass.services.async_call('input_number', 'set_value', {
        'entity_id': 'input_number.washing_machine_' + name + '_since',
        'value': int(dt_util.utcnow().timestamp()) - seconds,
    }, blocking=True)


async def arm(hass):
    hass.states.async_set(POWER, '100')
    await hass.async_block_till_done()
    await age(hass, 'high', 121)
    await reconcile(hass)
    assert hass.states.get(RUNNING).state == 'on'


async def test_idle_startup_has_known_state_without_finish_notification(hass, washer):
    await reconcile(hass)
    assert hass.states.get(SENSOR).state == 'on'
    assert washer == []


async def test_fast_finish_once_only_after_confirmed_cycle(hass, washer):
    await arm(hass)
    hass.states.async_set(POWER, '0')
    await hass.async_block_till_done()
    await age(hass, 'zero', 119)
    await reconcile(hass)
    assert hass.states.get(RUNNING).state == 'on'
    await age(hass, 'zero', 121)
    await reconcile(hass)
    await reconcile(hass)
    assert hass.states.get(SENSOR).state == 'on'
    assert len(washer) == 2
    assert 'below 1 W' in washer[-1]


async def test_standby_fallback_includes_exactly_ten_watts(hass, washer):
    await arm(hass)
    hass.states.async_set(POWER, '10')
    await hass.async_block_till_done()
    await age(hass, 'low', 959)
    await reconcile(hass)
    assert hass.states.get(RUNNING).state == 'on'
    await age(hass, 'low', 961)
    await reconcile(hass)
    assert hass.states.get(RUNNING).state == 'off'
    assert '16 min' in washer[-1]


async def test_pause_and_resumed_load_cancel_finish_timers(hass, washer):
    await arm(hass)
    hass.states.async_set(POWER, '0')
    await hass.async_block_till_done()
    await age(hass, 'zero', 119)
    hass.states.async_set(POWER, '100')
    await hass.async_block_till_done()
    assert hass.states.get('input_number.washing_machine_zero_since').state == '0.0'
    assert hass.states.get('input_number.washing_machine_low_since').state == '0.0'
    assert hass.states.get(RUNNING).state == 'on'
    assert len(washer) == 1


@pytest.mark.parametrize('bad', ['unknown', 'unavailable'])
async def test_missing_measurement_never_completes_cycle(hass, washer, bad):
    await arm(hass)
    await age(hass, 'low', 1000)
    await age(hass, 'zero', 200)
    hass.states.async_set(POWER, bad)
    await hass.async_block_till_done()
    assert hass.states.get(RUNNING).state == 'on'
    assert hass.states.get(SENSOR).state == 'unavailable'
    hass.states.async_set(POWER, '0')
    await hass.async_block_till_done()
    assert hass.states.get(SENSOR).state == 'off'
    assert len(washer) == 1


async def test_reconcile_preserves_running_and_existing_deadline(hass, washer):
    # Reconciliation uses restored helper values rather than a volatile delay timer.
    await hass.services.async_call('input_boolean', 'turn_on', {'entity_id': RUNNING}, blocking=True)
    await age(hass, 'zero', 60)
    await age(hass, 'low', 60)
    await reconcile(hass)
    assert hass.states.get(SENSOR).state == 'off'
    assert washer == []
    await age(hass, 'zero', 121)
    await reconcile(hass)
    assert hass.states.get(SENSOR).state == 'on'
    assert len(washer) == 1


async def test_helpers_restore_running_cycle_after_restart(hass):
    config = yaml.safe_load(PACKAGE.read_text(encoding='utf-8-sig'))
    stamp = int(dt_util.utcnow().timestamp()) - 60
    mock_restore_cache(hass, [
        State(RUNNING, 'on'),
        State('input_number.washing_machine_high_since', '0'),
        State('input_number.washing_machine_low_since', str(stamp)),
        State('input_number.washing_machine_zero_since', str(stamp)),
    ])
    hass.states.async_set(POWER, '0')
    for domain in ('input_boolean', 'input_number', 'template'):
        assert await async_setup_component(hass, domain, {domain: config[domain]})
    await hass.async_block_till_done()
    assert hass.states.get(RUNNING).state == 'on'
    assert hass.states.get(SENSOR).state == 'off'
    assert float(hass.states.get('input_number.washing_machine_zero_since').state) == stamp
