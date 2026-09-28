from pathlib import Path

import pytest
import yaml
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "homeassistant/locations/house/packages/shading_v1.yaml"
COVERS = [
    "cover.bedroom_roller_shutter",
    "cover.kids_room_roller_shutter",
    "cover.workshop_roller_shutter",
    "cover.kitchen_roller_shutter",
    "cover.living_room_roller_shutter",
]
CONTACTS = {
    "bedroom": "binary_sensor.bedroom_window_sensor_contact",
    "kids_room": "binary_sensor.kids_room_window_sensor_contact",
    "workshop": "binary_sensor.workshop_window_sensor_contact",
    "kitchen": "binary_sensor.kitchen_window_sensor_contact",
    "living_room": "binary_sensor.living_room_door_sensor_contact",
}


@pytest.fixture
async def shading(hass: HomeAssistant):
    package = yaml.safe_load(PACKAGE.read_text())
    calls = []

    for entity_id in COVERS:
        hass.states.async_set(entity_id, "open", {"current_position": 100})
    for entity_id in CONTACTS.values():
        hass.states.async_set(entity_id, "off")

    async def cover_service(call):
        targets = call.data["entity_id"]
        if isinstance(targets, str):
            targets = [targets]
        calls.extend(
            (call.service, target, call.data.get("position")) for target in targets
        )

    hass.services.async_register("cover", "set_cover_position", cover_service)
    hass.services.async_register("cover", "stop_cover", cover_service)
    assert await async_setup_component(
        hass, "input_boolean", {"input_boolean": package["input_boolean"]}
    )
    assert await async_setup_component(hass, "script", {"script": package["script"]})
    assert await async_setup_component(
        hass, "automation", {"automation": package["automation"]}
    )
    await hass.async_block_till_done()
    yield package, calls
    await hass.services.async_call(
        "automation",
        "turn_off",
        {
            "entity_id": [
                state.entity_id for state in hass.states.async_all("automation")
            ],
            "stop_actions": True,
        },
        blocking=True,
    )


async def enable(hass):
    await hass.services.async_call(
        "input_boolean",
        "turn_on",
        {"entity_id": "input_boolean.shading_automation_enabled"},
        blocking=True,
    )


async def run_script(hass, service, data=None):
    await hass.services.async_call("script", service, data or {}, blocking=True)
    await hass.async_block_till_done()


async def test_disabled_by_default_sends_no_commands(hass, shading):
    _, calls = shading
    await run_script(hass, "shading_apply_night_positions")
    await run_script(hass, "shading_open_morning")
    assert calls == []


async def test_night_positions_and_passage_protection(hass, shading):
    _, calls = shading
    await enable(hass)
    hass.states.async_set(CONTACTS["kids_room"], "on")
    hass.states.async_set(CONTACTS["workshop"], "unknown")
    hass.states.async_set(CONTACTS["living_room"], "on")

    await run_script(hass, "shading_apply_night_positions")

    assert calls == [
        ("set_cover_position", COVERS[0], 0),
        ("set_cover_position", COVERS[1], 20),
        ("set_cover_position", COVERS[3], 0),
    ]


async def test_window_event_only_re_evaluates_its_shutter(hass, shading):
    _, calls = shading
    await enable(hass)
    hass.states.async_set(CONTACTS["kids_room"], "on")

    await run_script(
        hass,
        "shading_apply_night_positions",
        {"changed_contact": CONTACTS["kids_room"]},
    )

    assert calls == [("set_cover_position", COVERS[1], 20)]


async def test_morning_excludes_bedroom(hass, shading):
    _, calls = shading
    await enable(hass)

    await run_script(hass, "shading_open_morning")

    assert calls == [
        ("set_cover_position", entity_id, 100) for entity_id in COVERS[1:]
    ]


async def test_opening_living_room_passage_stops_closing_shutter(hass, shading):
    _, calls = shading
    await enable(hass)
    hass.states.async_set(COVERS[-1], "closing", {"current_position": 50})
    hass.states.async_set(CONTACTS["living_room"], "on")
    await hass.async_block_till_done()

    assert calls == [("stop_cover", COVERS[-1], None)]
