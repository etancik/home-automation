# Heating lab and migration notes

Target: Home Assistant **2026.9.2**, the stable Core release checked on 2026-09-13 using [the official release manifest](https://version.home-assistant.io/stable.json). Python and HA dependencies run in Docker; the host only needs Docker with Linux containers and Python 3.10+.

## Start

From the repository root:

```sh
python lab/prepare.py
docker compose -f lab/compose.yaml up -d
python lab/run_smoke.py
```

Open http://127.0.0.1:18123 and create a **lab-only** account through HA onboarding. The YAML dashboard contains the enable switch, boiler state, safety reset, bedroom temperature/window controls and floor thermostat. Successful automated scenarios leave heating disabled. To explore manually, enable `input_boolean.heating_enabled`, set the bedroom target to 21 and lower its simulated temperature to 19.

`lab/prepare.py` copies the real house `heating_*.yaml` packages into an ignored runtime directory. It preserves the lab database, helper state and account. **After editing packages, rerun prepare and restart HA**:

```sh
python lab/prepare.py
docker compose -f lab/compose.yaml restart ha
```

The lab has its own Mosquitto broker and deterministic MQTT devices with the same entity IDs and command topics as the house. It does not copy production credentials, `.storage`, databases, non-heating automations or the Zigbee2MQTT deployment command. HA, MQTT and the simulator use a Docker `internal` network with no external gateway. The only published port is a localhost TCP forwarder with a fixed destination, the lab HA. No host networking, USB devices, MQTT bridges or household integrations are configured. The forwarder is an additional small container because direct publication from an internal network did not work on the tested Docker Desktop setup.

The bootstrap custom integration configures this broker through the HA config flow and generates a local test API token in ignored `lab/.runtime/config/.lab-token`. The token lasts one day and is regenerated on HA restart. Never copy the bootstrap integration or the lab runtime to production. Its custom-integration warning is expected.

Stop containers while keeping the local lab state:

```sh
docker compose -f lab/compose.yaml down
```

## Repeatable tests

```sh
python tests/run.py
python lab/run_smoke.py
```

The first command builds the pinned test runtime, runs pytest with actual HA automation/template/script/helper integrations and blocked network access, and validates the complete house configuration with dummy location secrets. The second command requires the running lab; it tests real MQTT integrations, native generic thermostats, acknowledgement failure and two actual HA shutdown/start cycles. One restart preserves an active deadline; the other deliberately keeps HA stopped until that deadline expires. Temperatures are explicit inputs, not a thermal model.

Run `python tests/run.py` locally before every push. GitHub Actions invokes that exact same entry point and then runs the live lab, so CI confirms a locally tested result instead of maintaining a separate copy of the unit and configuration-check commands. Deployment branches are excluded from push runs. The workflow has read-only repository permissions and performs no deployment.

The regression fixture `tests/fixtures/heating_before.yaml` preserves the original heating automations at commit `6d2016ade0cfbe97281fda5408249e5d64312798`. A test evaluates the original boiler-start template and demonstrates that an OFF room could request heat. Other tests evaluate the new production packages. This is not a claim that every historical defect was reproduced against a complete old HA instance.

Coverage includes:

| Scenario | Verification |
| --- | --- |
| Cold active room starts boiler; OFF room does not | pytest + live MQTT |
| Boiler start below target minus 1 °C; continued demand until emitters stop | pytest + live MQTT |
| All zones satisfied; summer disable | pytest + live MQTT/reset |
| Window closes and restores off/heat/auto | pytest; auto also through MQTT |
| Unknown contact or invalid/unavailable temperature | pytest |
| Unacknowledged ON and OFF, relay disappears | pytest; failed ON also through MQTT |
| Four-hour limit locks despite continuing demand | simulated time in pytest; shortened real deadline in lab |
| Restart retains deadline; deadline expires while HA is stopped | actual HA process restarts |
| Floor thermostat, physical relay state, window interlock | actual generic thermostat + pytest |

For manual fault injection, use Python in the simulator container. On shells that preserve JSON quoting:

```sh
docker compose -f lab/compose.yaml exec simulator python /lab/simulator.py '{"room":"bedroom","temperature":19}'
docker compose -f lab/compose.yaml exec simulator python /lab/simulator.py '{"room":"bedroom","available":"offline"}'
docker compose -f lab/compose.yaml exec simulator python /lab/simulator.py '{"relay":"laundry_room_boiler_controller_l2","fail":"off"}'
```

Set `available` to `online` to recover a room. Set `fail` to an empty string to recover the relay. The dashboard is easier for temperature/window changes on shells with awkward JSON quoting. `lab/smoke.py` contains shell-independent examples using the local HA API. Fault flags reset on simulator restart. For useful retained state, restart HA alone during tests, not the simulator or broker.

## Production decomposition

| Package | Responsibility |
| --- | --- |
| `heating_boiler.yaml` | Eligible-zone demand, enable switch, acknowledgement, deadline, safety lock, startup readiness |
| `heating_floor.yaml` | Two native thermostats and bathroom external temperature template |
| `heating_windows.yaml` | Remember and restore HVAC modes when contacts block heating |
| `heating_sensor_sync.yaml` | Send external temperatures and reconcile after HA/MQTT restart and every five minutes |

The main configuration loads each file as a separate package with `!include_dir_named packages`. This avoids shallow domain-key overwrites from `!include_dir_merge_named`. The house deployment subtree is self-contained; it no longer references the absent `../../core/packages`. Those core files contained CO2 customization/thresholds and a template using an undefined `co2_value`. They remain in the repository but are not imported into the house. Before deployment, check whether the actual installation has any manually added core files or references to these CO2 helpers. This change does not reconstruct those unrelated features.

## Deliberate behavior changes

- A zone can start the boiler only in `heat`/`auto`, with a numeric external temperature and target, known closed contacts and an active emitter. OFF zones no longer start heating. The outer start threshold remains strictly below target minus 1 °C. Continued operation follows active eligible emitters.
- The floor thermostat retains `cold_tolerance: 1.0` and `hot_tolerance: 0`. In this HA implementation, equality at the target does not switch it off; temperature must exceed the target. Existing entity IDs and unique IDs are retained. Removing forced startup `heat` allows the previous HVAC mode to restore. On a completely new lab, floors initially use OFF and the default 4 °C target until explicitly set.
- `heating_enabled` initially defaults OFF, then restores on future restarts. This is the master boiler enable, not an instruction to change all room setpoints or floor relay states.
- A deadline is saved **before** commanding boiler ON. It is not extended by another demand event. A four-hour run, unknown run duration or missing relay acknowledgement locks heating. An unavailable relay during a known run also latches the lock. A failed OFF command preserves the deadline, reports the fault and leaves the actual ON state visible; software cannot force broken hardware off.
- Startup waits up to 30 seconds for the configured devices before reconciling. It distinguishes temporary startup unavailability from an outage during an active run. If inputs remain missing, the normal conservative logic takes over. A deadline that expires while HA is down is handled after this startup grace period; this is not an independent hardware watchdog.
- Safety acknowledgement uses `script.heating_reset_safety` and only succeeds with confirmed relay OFF. If heating remains enabled and there is cold demand, acknowledgement can start a new run. Disable heating first when recovering faults for inspection.
- Unknown window/contact state blocks a zone. The previously selected mode survives the block and HA restart via helpers. A mode change while the window remains open is overridden by the interlock; it is not remembered as a new future preference.
- The bathroom template requires the external sensor, rather than falling back to a TRV value that may itself contain the last external reading. It has `state_class: measurement` for statistics.

## Limits and rollout

These tests verify configuration logic and HA/MQTT behavior, not the physical boiler, valve travel, hydraulic flow or the exact firmware behavior of the installed TRVs. The simulator acknowledges commands and emulates hysteresis; it is not a Zigbee firmware emulator. Actual relay state feedback must also be verified before deployment.

Numeric stale readings are still a separate unresolved case. The lab sensors expire after 60 seconds; this **does not configure expiry on production Zigbee2MQTT sensors**. Production availability/last-seen behavior and normal reporting intervals need to be measured before choosing a meaningful freshness limit. A numeric but stale production value can remain eligible. Temperature plausibility limits and hardware minimum cycling times also require device/house evidence.

No update has been deployed to the house. Before rollout: make and export a recoverable HA backup including `.storage` and Zigbee2MQTT state, compare this branch with the then-current deployment branch, and run configuration validation on the target installation. Keep the boiler physically disabled for the first configuration/entity/relay checks. Enable live heating only during supervised commissioning, with a known rollback. The existing HA-start Zigbee2MQTT deployment automation remains in the house config; it is excluded from the lab.

Source baseline is `master` at the commit above. The deployment branch at 188d57a6a618ea658da7fc7f4286a5472144e505 contains a two-minute washing-machine start delay; this is now preserved in the washing_machine package. The valve synchronization queue limit of 10 is also retained. Do not overwrite newer deployment changes with this snapshot wholesale.

Backups, historical-data analysis, EV control and blinds remain separate follow-up work. No production data was used or claimed to be analyzed in this lab implementation.

For future HA updates, change the image versions in `lab/compose.yaml`, `tests/Dockerfile`, `tests/run.py` and the workflow; align `tests/requirements.txt` with a compatible pytest HA plugin. Run both suites before upgrading the real installation. [HA packages documentation](https://www.home-assistant.io/docs/configuration/packages/) explains the package merge semantics; [Generic Thermostat](https://www.home-assistant.io/integrations/generic_thermostat/) describes the native controller options.
