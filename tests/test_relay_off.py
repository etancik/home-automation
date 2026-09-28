from conftest import BOILER

async def test_unacknowledged_off_locks_and_keeps_deadline(rig):
    await rig.enabled()
    rig.room()
    await rig.settle()
    deadline = rig.hass.states.get('input_datetime.heating_boiler_deadline').attributes['timestamp']
    rig.failed.add('off')
    await rig.enabled(False)
    assert rig.hass.states.is_state(BOILER, 'on')
    assert rig.hass.states.is_state('input_boolean.heating_safety_lock', 'on')
    assert rig.hass.states.get('input_datetime.heating_boiler_deadline').attributes['timestamp'] == deadline
    await rig.hass.services.async_call('script', 'heating_reset_safety', {}, blocking=True)
    assert rig.hass.states.is_state('input_boolean.heating_safety_lock', 'on')
    rig.failed.clear()
    rig.room(temp=18)
    await rig.settle()
    assert rig.hass.states.is_state(BOILER, 'off')
    assert rig.hass.states.is_state('input_boolean.heating_safety_lock', 'on')
