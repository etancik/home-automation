from pathlib import Path

import pytest
import yaml
from homeassistant.helpers.template import Template
from homeassistant.setup import async_setup_component
from homeassistant.components.template import DATA_COORDINATORS

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = yaml.safe_load((ROOT / 'homeassistant/locations/house/packages/house_diagnostics.yaml').read_text())
SENSORS = {s['name']: s for s in PACKAGE['template'][0]['sensor']}
BOILER = 'switch.laundry_room_boiler_controller_l2'


@pytest.fixture
async def diagnostics(hass):
    for sensor in list(SENSORS.values())[:8]:
        climate = sensor['attributes']['climate_entity']
        thermometer = sensor['attributes']['temperature_entity']
        hass.states.async_set(climate, 'heat', {'temperature': 21, 'hvac_action': 'idle'})
        hass.states.async_set(thermometer, '21')
    for room in ['bedroom', 'kids_room', 'workshop', 'entrance', 'living_room']:
        hass.states.async_set('input_boolean.heating_window_' + room, 'off')
    for contact in ['bedroom_window','kids_room_window','workshop_window','entrance_door','kitchen_window','living_room_door']:
        hass.states.async_set('binary_sensor.' + contact + '_sensor_contact', 'off')
    for entity, value in {
        BOILER: 'off', 'input_boolean.heating_enabled': 'on',
        'input_boolean.heating_safety_lock': 'off', 'input_boolean.heating_controller_ready': 'on',
        'switch.floor_heating_controller_l1': 'off', 'switch.floor_heating_controller_l2': 'off',
        'input_boolean.ev_dynamic_load_balancing_enabled':'on',
        'sensor.go_econtroller_917809_home_power':'300',
        'sensor.go_echarger_600187_power_total':'0',
        'sensor.go_echarger_600187_car_state':'Idle',
        'sensor.go_echarger_600187_error_state':'NoError',
    }.items():
        hass.states.async_set(entity, value)
    for entity in [
        'binary_sensor.living_room_smoke_detector_smoke', 'binary_sensor.shellyplussmoke_28562fcca298_smoke',
        'binary_sensor.downstairs_bathroom_leak_sensor_water_leak', 'binary_sensor.upstairs_bathroom_leak_sensor_water_leak',
        'binary_sensor.laundry_room_leak_sensor_water_leak', 'binary_sensor.kitchen_sink_leak_sensor_water_leak',
    ]:
        hass.states.async_set(entity, 'off')
    assert await async_setup_component(hass, 'template', {'template': PACKAGE['template']})
    await hass.async_block_till_done()
    await hass.async_start()
    yield
    # YAML template coordinators are normally stopped by template reload,
    # which the isolated fixture does not run on shutdown.
    for coordinator in hass.data.get(DATA_COORDINATORS, []):
        await coordinator.async_shutdown()
    await hass.async_stop(force=True)


@pytest.mark.parametrize('temperature,emitter,boiler,status,start,keep', [
    (19.9, 'heating','off','Žádá start',True,True),
    (20, 'heating','off','Čeká na pokles o 1 °C',False,True),
    (20.8, 'heating','on','Udržuje běh',False,True),
    (21, 'heating','on','Dosaženo',False,False),
    (19, 'idle','off','Čeká na ventil',False,False),
])
async def test_room_matches_boiler_hysteresis(hass, diagnostics, temperature, emitter, boiler, status, start, keep):
    hass.states.async_set('sensor.bedroom_temperature_sensor_temperature', str(temperature))
    hass.states.async_set('climate.bedroom_radiator_heat_valve','heat',{'temperature':21,'hvac_action':emitter})
    hass.states.async_set(BOILER,boiler)
    await hass.async_block_till_done()
    result=hass.states.get('sensor.heating_debug_bedroom')
    assert result.state == status
    assert result.attributes['start_requested'] is start
    assert result.attributes['keep_requested'] is keep


@pytest.mark.parametrize('entity,value,status', [
    ('binary_sensor.bedroom_window_sensor_contact','on','Otevřené okno'),
    ('binary_sensor.bedroom_window_sensor_contact','unavailable','Neznámý stav okna'),
    ('sensor.bedroom_temperature_sensor_temperature','unavailable','Chybí data'),
    ('climate.bedroom_radiator_heat_valve','off','Vypnuto'),
    ('input_boolean.heating_window_bedroom','on','Čeká na obnovu po okně'),
])
async def test_blocks_do_not_claim_heat_demand(hass, diagnostics, entity, value, status):
    hass.states.async_set('sensor.bedroom_temperature_sensor_temperature','18')
    attrs={'temperature':21,'hvac_action':'heating'}
    hass.states.async_set('climate.bedroom_radiator_heat_valve','heat',attrs)
    if entity == 'input_boolean.heating_window_bedroom':
        # The window controller holds HVAC off until restoration finishes.
        hass.states.async_set('climate.bedroom_radiator_heat_valve','off',attrs)
    hass.states.async_set(entity,value,attrs if entity.startswith('climate.') else {})
    await hass.async_block_till_done()
    result=hass.states.get('sensor.heating_debug_bedroom')
    assert result.state == status
    assert not result.attributes['start_requested']
    assert not result.attributes['keep_requested']


async def test_floor_uses_relay_instead_of_climate_action(hass, diagnostics):
    hass.states.async_set('sensor.living_room_temperature_sensor_temperature','19')
    hass.states.async_set('switch.floor_heating_controller_l1','on')
    await hass.async_block_till_done()
    assert hass.states.get('sensor.heating_debug_living_room').attributes['start_requested']


async def test_reason_explains_global_guard_and_actual_relay_separately(hass, diagnostics):
    hass.states.async_set('input_boolean.heating_safety_lock','on')
    await hass.async_block_till_done()
    state=hass.states.get('sensor.house_boiler_reason')
    assert state.state == 'Povel vypnutý'
    assert 'Bezpečnostní zámek' in state.attributes['reason']


async def test_attention_flags_low_target_but_not_intentional_entrance_15(hass, diagnostics):
    hass.states.async_set('climate.kids_room_radiator_heat_valve','heat',{'temperature':7,'hvac_action':'idle'})
    hass.states.async_set('climate.entrance_radiator_heat_valve','heat',{'temperature':15,'hvac_action':'idle'})
    await hass.async_block_till_done()
    result=hass.states.get('sensor.house_debug_attention')
    assert int(result.state) == len(result.attributes['issues']) == 1
    assert result.attributes['issues'][0]['entity'] == 'climate.kids_room_radiator_heat_valve'


async def test_active_water_alarm_is_first_attention_item(hass, diagnostics):
    hass.states.async_set('binary_sensor.laundry_room_leak_sensor_water_leak','on')
    await hass.async_block_till_done()
    issues=hass.states.get('sensor.house_debug_attention').attributes['issues']
    assert issues[0]['entity'] == 'binary_sensor.laundry_room_leak_sensor_water_leak'
    assert issues[0]['reason'] == 'Aktivní alarm'


async def test_event_snapshots_ignore_attributes_recovery_and_keep_only_16(hass, diagnostics):
    for i in range(20):
        hass.states.async_set('input_boolean.ev_dynamic_load_balancing_enabled','off' if i % 2 == 0 else 'on')
        await hass.async_block_till_done()
    result=hass.states.get('sensor.house_debug_events')
    assert len(result.attributes['events']) == 16
    before=result.attributes['events']
    hass.states.async_set('input_boolean.ev_dynamic_load_balancing_enabled','on',{'friendly_name':'New name'})
    hass.states.async_set('input_boolean.ev_dynamic_load_balancing_enabled','unavailable')
    await hass.async_block_till_done()
    hass.states.async_set('input_boolean.ev_dynamic_load_balancing_enabled','on')
    await hass.async_block_till_done()
    assert hass.states.get('sensor.house_debug_events').attributes['events'] == before


async def test_dashboard_templates_render_without_errors(hass, diagnostics):
    config=yaml.safe_load((ROOT/'homeassistant/locations/house/dashboards/house_debug.yaml').read_text())
    def walk(value):
        if isinstance(value,dict):
            if value.get('type') == 'markdown':
                rendered=Template(value['content'],hass).async_render()
                if value.get('title') == 'Místnosti · proč topí / netopí':
                    assert len([line for line in rendered.splitlines() if line.startswith('|')]) == 10
            for child in value.values():
                walk(child)
        elif isinstance(value,list):
            for child in value:
                walk(child)
    walk(config)
