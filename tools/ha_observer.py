"""Read-only Home Assistant health and anomaly report.

Credentials are accepted from HA_OBSERVER_URL/HA_OBSERVER_TOKEN or stored outside
the repository using Windows DPAPI by the ``setup`` command.
"""

from __future__ import annotations

import argparse
import base64
import ctypes
from ctypes import wintypes
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import getpass
import json
import os
from pathlib import Path
import statistics
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


TEMPERATURE_ENTITIES = (
    "sensor.bedroom_temperature_sensor_temperature",
    "sensor.kids_room_temperature_sensor_temperature",
    "sensor.workshop_temperature_sensor_temperature",
    "sensor.entrance_temperature_sensor_temperature",
    "sensor.downstairs_bathroom_temperature_sensor_temperature",
    "sensor.upstairs_bathroom_temperature_sensor_temperature",
    "sensor.living_room_temperature_sensor_temperature",
)
CONTACT_ENTITIES = (
    "binary_sensor.bedroom_window_sensor_contact",
    "binary_sensor.kids_room_window_sensor_contact",
    "binary_sensor.workshop_window_sensor_contact",
    "binary_sensor.entrance_door_sensor_contact",
    "binary_sensor.kitchen_window_sensor_contact",
    "binary_sensor.living_room_door_sensor_contact",
)
COVER_ENTITIES = (
    "cover.bedroom_roller_shutter",
    "cover.kids_room_roller_shutter",
    "cover.workshop_roller_shutter",
    "cover.kitchen_roller_shutter",
    "cover.living_room_roller_shutter",
)
HEATING_ENTITIES = (
    "switch.laundry_room_boiler_controller_l2",
    "input_boolean.heating_enabled",
    "input_boolean.heating_safety_lock",
)
CRITICAL_ENTITIES = (
    *TEMPERATURE_ENTITIES,
    *CONTACT_ENTITIES,
    *COVER_ENTITIES,
    *HEATING_ENTITIES,
)
HISTORY_ENTITIES = (
    "switch.laundry_room_boiler_controller_l2",
    *TEMPERATURE_ENTITIES,
    *COVER_ENTITIES,
)


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    entity_id: str | None = None


class HomeAssistantError(RuntimeError):
    """A useful, secret-free Home Assistant client error."""


class HomeAssistantClient:
    def __init__(self, url: str, token: str, timeout: int = 20) -> None:
        self.url = url.rstrip("/")
        self._token = token
        self.timeout = timeout

    def get(self, path: str, params: dict[str, str] | None = None) -> Any:
        query = f"?{urlencode(params)}" if params else ""
        request = Request(
            f"{self.url}{path}{query}",
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
            method="GET",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code == 401:
                raise HomeAssistantError("Home Assistant rejected the observer token (HTTP 401)") from exc
            raise HomeAssistantError(f"Home Assistant API returned HTTP {exc.code}") from exc
        except URLError as exc:
            raise HomeAssistantError(f"Cannot reach Home Assistant at {self.url}: {exc.reason}") from exc


def _credential_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home()))
    return base / "HomeAutomationObserver" / "credentials.dpapi"


if sys.platform == "win32":
    class _DataBlob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _dpapi(value: bytes, decrypt: bool) -> bytes:
    if sys.platform != "win32":
        raise HomeAssistantError(
            "DPAPI credential storage is available only on Windows; use HA_OBSERVER_URL and HA_OBSERVER_TOKEN"
        )
    source_buffer = ctypes.create_string_buffer(value)
    source = _DataBlob(len(value), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_byte)))
    result = _DataBlob()
    description = wintypes.LPWSTR()
    if decrypt:
        ok = ctypes.windll.crypt32.CryptUnprotectData(  # type: ignore[attr-defined]
            ctypes.byref(source), ctypes.byref(description), None, None, None, 0, ctypes.byref(result)
        )
    else:
        ok = ctypes.windll.crypt32.CryptProtectData(  # type: ignore[attr-defined]
            ctypes.byref(source), "Home Automation Observer", None, None, None, 0, ctypes.byref(result)
        )
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(result.pbData)  # type: ignore[attr-defined]
        if description:
            ctypes.windll.kernel32.LocalFree(description)  # type: ignore[attr-defined]


def save_credentials(url: str, token: str) -> Path:
    path = _credential_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"url": url.rstrip("/"), "token": token}).encode()
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(base64.b64encode(_dpapi(payload, decrypt=False)))
    temporary.replace(path)
    return path


def load_credentials() -> tuple[str, str]:
    if url := os.environ.get("HA_OBSERVER_URL"):
        token = os.environ.get("HA_OBSERVER_TOKEN")
        if not token:
            raise HomeAssistantError("HA_OBSERVER_TOKEN is missing")
        return url.rstrip("/"), token
    path = _credential_path()
    if not path.exists():
        raise HomeAssistantError(f"Observer credentials are not configured; run: python tools/ha_observer.py setup")
    payload = _dpapi(base64.b64decode(path.read_bytes()), decrypt=True)
    stored = json.loads(payload)
    return stored["url"], stored["token"]


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or value in {"", "unknown", "unavailable"}:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _number(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def analyze_snapshot(states: list[dict[str, Any]], now: datetime) -> list[Finding]:
    by_id = {state["entity_id"]: state for state in states}
    findings: list[Finding] = []

    for entity_id in CRITICAL_ENTITIES:
        state = by_id.get(entity_id)
        if state is None:
            findings.append(Finding("warning", "missing_entity", "Expected entity is missing", entity_id))
        elif state.get("state") in {"unknown", "unavailable"}:
            findings.append(Finding("critical", "unavailable", f"Entity is {state['state']}", entity_id))

    for entity_id in TEMPERATURE_ENTITIES:
        state = by_id.get(entity_id)
        if not state or state.get("state") in {"unknown", "unavailable"}:
            continue
        value = _number(state.get("state"))
        if value is not None and not 5 <= value <= 35:
            findings.append(Finding("critical", "temperature_range", f"Implausible indoor temperature {value:g} °C", entity_id))
        updated = _parse_datetime(state.get("last_updated"))
        if updated and now - updated.astimezone(timezone.utc) > timedelta(hours=6):
            findings.append(Finding("warning", "stale_temperature", "Temperature has not updated for over 6 hours", entity_id))

    for state in states:
        entity_id = state.get("entity_id", "")
        attrs = state.get("attributes", {})
        value = _number(state.get("state"))
        if attrs.get("device_class") == "battery" and value is not None and value < 20:
            findings.append(Finding("warning", "low_battery", f"Battery is at {value:g}%", entity_id))
        if attrs.get("device_class") == "carbon_dioxide" and value is not None:
            if value >= 2500:
                findings.append(Finding("critical", "co2_high", f"CO₂ is {value:g} ppm", entity_id))
            elif value >= 1500:
                findings.append(Finding("warning", "co2_elevated", f"CO₂ is {value:g} ppm", entity_id))

    safety = by_id.get("input_boolean.heating_safety_lock", {}).get("state")
    if safety == "on":
        findings.append(Finding("critical", "heating_safety_lock", "Heating safety lock is active", "input_boolean.heating_safety_lock"))
    boiler = by_id.get("switch.laundry_room_boiler_controller_l2", {}).get("state")
    enabled = by_id.get("input_boolean.heating_enabled", {}).get("state")
    if boiler == "on" and enabled != "on":
        findings.append(Finding("critical", "boiler_without_enable", "Boiler relay is on while heating is disabled", "switch.laundry_room_boiler_controller_l2"))

    living_cover = by_id.get("cover.living_room_roller_shutter", {}).get("state")
    living_door = by_id.get("binary_sensor.living_room_door_sensor_contact", {}).get("state")
    if living_cover == "closing" and living_door != "off":
        findings.append(Finding("critical", "passage_closing", "Living-room shutter is closing while passage is not confirmed closed", "cover.living_room_roller_shutter"))

    backup = by_id.get("sensor.backup_last_successful_automatic_backup")
    if backup:
        successful = _parse_datetime(backup.get("state"))
        if successful is None:
            findings.append(Finding("warning", "backup_unknown", "Last successful automatic backup is unknown", backup["entity_id"]))
        elif now - successful.astimezone(timezone.utc) > timedelta(hours=36):
            age = now - successful.astimezone(timezone.utc)
            findings.append(Finding("critical", "backup_stale", f"Last successful backup is {age.days}d {age.seconds // 3600}h old", backup["entity_id"]))

    return findings


def analyze_history(history: list[list[dict[str, Any]]]) -> list[Finding]:
    findings: list[Finding] = []
    for series in history:
        if not series:
            continue
        entity_id = series[0].get("entity_id")
        unavailable = sum(item.get("state") in {"unknown", "unavailable"} for item in series)
        if unavailable:
            findings.append(Finding("warning", "availability_flap", f"Entered unknown/unavailable {unavailable} time(s) in the selected period", entity_id))

        if entity_id == "switch.laundry_room_boiler_controller_l2":
            transitions = [item for item in series if item.get("state") in {"on", "off"}]
            on_times = [_parse_datetime(item.get("last_changed")) for item in transitions if item.get("state") == "on"]
            on_times = [value for value in on_times if value]
            if len(on_times) > 20:
                findings.append(Finding("warning", "boiler_many_cycles", f"Boiler started {len(on_times)} times", entity_id))
            short_runs = 0
            for current, following in zip(transitions, transitions[1:]):
                if current.get("state") != "on" or following.get("state") != "off":
                    continue
                start = _parse_datetime(current.get("last_changed"))
                stop = _parse_datetime(following.get("last_changed"))
                if start and stop and timedelta(0) <= stop - start < timedelta(minutes=5):
                    short_runs += 1
            if short_runs >= 2:
                findings.append(Finding("warning", "boiler_short_cycles", f"Detected {short_runs} boiler runs shorter than 5 minutes", entity_id))

        if entity_id in TEMPERATURE_ENTITIES:
            values = [_number(item.get("state")) for item in series]
            numeric = [value for value in values if value is not None]
            if len(numeric) >= 3:
                spread = max(numeric) - min(numeric)
                if spread > 8:
                    findings.append(Finding("warning", "temperature_spread", f"Temperature range was {spread:.1f} °C (median {statistics.median(numeric):.1f} °C)", entity_id))
    return findings


def collect_report(client: HomeAssistantClient, history_hours: int) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    config = client.get("/api/config")
    states = client.get("/api/states")
    findings = analyze_snapshot(states, now)
    history: list[list[dict[str, Any]]] = []
    if history_hours:
        start = (now - timedelta(hours=history_hours)).isoformat()
        history = client.get(
            f"/api/history/period/{start}",
            {
                "filter_entity_id": ",".join(HISTORY_ENTITIES),
                "minimal_response": "",
                "no_attributes": "",
            },
        )
        findings.extend(analyze_history(history))
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda item: (severity_order[item.severity], item.code, item.entity_id or ""))
    return {
        "generated_at": now.isoformat(),
        "home_assistant_version": config.get("version"),
        "history_hours": history_hours,
        "entity_count": len(states),
        "findings": [asdict(item) for item in findings],
    }


def render_report(report: dict[str, Any]) -> str:
    findings = report["findings"]
    counts = {level: sum(item["severity"] == level for item in findings) for level in ("critical", "warning", "info")}
    lines = [
        f"Home Assistant {report.get('home_assistant_version', 'unknown')} observer report",
        f"Generated: {report['generated_at']}",
        f"Entities: {report['entity_count']}; critical: {counts['critical']}; warnings: {counts['warning']}",
    ]
    if not findings:
        lines.append("No anomaly matched the configured checks.")
    for item in findings:
        entity = f" [{item['entity_id']}]" if item.get("entity_id") else ""
        lines.append(f"- {item['severity'].upper()} {item['code']}{entity}: {item['message']}")
    return "\n".join(lines)


def command_setup(args: argparse.Namespace) -> int:
    url = input(f"Home Assistant URL [{args.url}]: ").strip() or args.url
    token = getpass.getpass("Long-lived access token (input is hidden): ").strip()
    if not token:
        raise HomeAssistantError("Token cannot be empty")
    client = HomeAssistantClient(url, token)
    response = client.get("/api/")
    if response.get("message") != "API running.":
        raise HomeAssistantError("Unexpected response from Home Assistant API")
    path = save_credentials(url, token)
    print(f"Read-only observer connection verified; encrypted credentials saved to {path}")
    return 0


def command_check(args: argparse.Namespace) -> int:
    url, token = load_credentials()
    report = collect_report(HomeAssistantClient(url, token), args.history_hours)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else render_report(report))
    if any(item["severity"] == "critical" for item in report["findings"]):
        return 2
    return 1 if report["findings"] else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    setup = subparsers.add_parser("setup", help="Validate and DPAPI-encrypt local API credentials")
    setup.add_argument("--url", default="http://homeassistant:8123")
    setup.set_defaults(handler=command_setup)
    check = subparsers.add_parser("check", help="Run the read-only anomaly report")
    check.add_argument("--history-hours", type=int, default=24)
    check.add_argument("--json", action="store_true")
    check.set_defaults(handler=command_check)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.handler(args)
    except (HomeAssistantError, ValueError, json.JSONDecodeError) as exc:
        print(f"ha-observer: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
