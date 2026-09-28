"""Lab-only MQTT config flow. Never included in production packages."""
import asyncio
from datetime import timedelta
import logging
from pathlib import Path
from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.components.mqtt.config_flow import CONFIG_DATAFLOW_SCHEMA

async def async_setup(hass, config):
    users = await hass.auth.async_get_users()
    user = next((u for u in users if u.name == 'Heating lab test runner' and u.system_generated), None)
    if user is None:
        user = await hass.auth.async_create_system_user('Heating lab test runner', group_ids=[GROUP_ID_ADMIN], local_only=True)
    refresh = next((t for t in user.refresh_tokens.values() if t.access_token_expiration == timedelta(days=1)), None)
    if refresh is None:
        refresh = await hass.auth.async_create_refresh_token(user, client_name='Heating lab local tests', access_token_expiration=timedelta(days=1))
    token = hass.auth.async_create_access_token(refresh)
    await hass.async_add_executor_job(Path(hass.config.path('.lab-token')).write_text, token)
    if hass.config_entries.async_entries('mqtt'):
        hass.states.async_set('binary_sensor.heating_lab_ready', 'on')
        return True
    for attempt in range(5):
        result = await hass.config_entries.flow.async_init('mqtt', context={'source':'user'})
        data = CONFIG_DATAFLOW_SCHEMA({
            'broker':'mqtt','port':1883,'username':'','password':'',
            'other_settings':{'set_client_cert':False,'set_ca_cert':'off'},
        })
        result = await hass.config_entries.flow.async_configure(result['flow_id'],data)
        if result['type']=='create_entry':
            hass.states.async_set('binary_sensor.heating_lab_ready', 'on')
            return True
        hass.config_entries.flow.async_abort(result['flow_id'])
        await asyncio.sleep(2)
    logging.getLogger(__name__).error('Could not configure isolated MQTT broker')
    return False
