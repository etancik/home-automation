# House backup and recovery

Configure **Settings > System > Backups** for daily encrypted backups to local
storage and Microsoft OneDrive, with backup before updates enabled. Include HA,
the database and installed apps, especially Zigbee2MQTT, Mosquitto and Git Pull.
Include `share` and `media` only if they contain irreplaceable data.

The measured full backup is **1.4 GB**. Three copies require about **4.2 GB**;
confirm OneDrive capacity before selecting retention. Save the emergency kit
outside HA. Keep encryption keys and credentials out of Git.

To verify: run `backup.create_automatic`, wait for completion, then check the
backup exists in both locations. A recent successful-backup sensor alone does
not prove the OneDrive copy is available. `packages/backup.yaml` keeps a persistent
notification active after failure and clears it after the next success.

Test recovery in a disposable HA OS VM isolated from production devices and
network services. Restore the backup using the emergency kit; verify HA starts,
entity IDs survive and Zigbee2MQTT data is present. Keep the production coordinator
disconnected. Record the outcome below.

Restore test: **pending**.
