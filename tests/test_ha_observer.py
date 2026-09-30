from datetime import datetime, timedelta, timezone

from tools.ha_observer import analyze_history, analyze_snapshot


def state(entity_id, value, *, hours_old=0, attributes=None):
    changed = datetime.now(timezone.utc) - timedelta(hours=hours_old)
    return {
        "entity_id": entity_id,
        "state": value,
        "last_changed": changed.isoformat(),
        "last_updated": changed.isoformat(),
        "attributes": attributes or {},
    }


def test_snapshot_detects_safety_and_environment_anomalies():
    now = datetime.now(timezone.utc)
    states = [
        state("input_boolean.heating_safety_lock", "on"),
        state("input_boolean.heating_enabled", "off"),
        state("switch.laundry_room_boiler_controller_l2", "on"),
        state("sensor.bedroom_temperature_sensor_temperature", "42", hours_old=7),
        state("sensor.test_battery", "12", attributes={"device_class": "battery"}),
        state("sensor.test_co2", "1700", attributes={"device_class": "carbon_dioxide"}),
        state("cover.living_room_roller_shutter", "closing"),
        state("binary_sensor.living_room_door_sensor_contact", "on"),
    ]
    codes = {finding.code for finding in analyze_snapshot(states, now)}
    assert {
        "heating_safety_lock",
        "boiler_without_enable",
        "temperature_range",
        "stale_temperature",
        "low_battery",
        "co2_elevated",
        "passage_closing",
    } <= codes


def test_history_detects_boiler_short_cycles_and_availability():
    start = datetime.now(timezone.utc) - timedelta(hours=1)
    series = [
        state("switch.laundry_room_boiler_controller_l2", "off"),
        state("switch.laundry_room_boiler_controller_l2", "on"),
        state("switch.laundry_room_boiler_controller_l2", "off"),
        state("switch.laundry_room_boiler_controller_l2", "on"),
        state("switch.laundry_room_boiler_controller_l2", "off"),
        state("switch.laundry_room_boiler_controller_l2", "unavailable"),
    ]
    for index, item in enumerate(series):
        item["last_changed"] = (start + timedelta(minutes=index * 2)).isoformat()
    codes = {finding.code for finding in analyze_history([series])}
    assert "boiler_short_cycles" in codes
    assert "availability_flap" in codes
