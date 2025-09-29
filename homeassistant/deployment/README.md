# Deployment Scripts for Multi-Location Home Assistant
# Use these to create Git subtree branches for each location

## Prerequisites Setup

Before creating the subtree branches, ensure your repository is clean:

```bash
cd /Users/i343783/git/experiments/home-automation
git add homeassistant/
git commit -m "Add multi-location Home Assistant structure"
```

## Creating House Configuration Branch

```bash
# Create the house branch using Git subtree
git subtree push --prefix=homeassistant/locations/house origin ha-config-house

# Or create it fresh if branch doesn't exist:
git subtree split --prefix=homeassistant/locations/house -b ha-config-house
git push origin ha-config-house
```

## Creating Flat Configuration Branch

```bash
# Create the flat branch using Git subtree  
git subtree push --prefix=homeassistant/locations/flat origin ha-config-flat

# Or create it fresh if branch doesn't exist:
git subtree split --prefix=homeassistant/locations/flat -b ha-config-flat
git push origin ha-config-flat
```

## SourceTree Setup

In SourceTree, add these as remotes for easy subtree management:

1. **House Remote:**
   - URL: `https://github.com/[your-username]/[your-repo].git`
   - Branch: `ha-config-house`
   - Local path: `homeassistant/locations/house`

2. **Flat Remote:**
   - URL: `https://github.com/[your-username]/[your-repo].git`
   - Branch: `ha-config-flat`
   - Local path: `homeassistant/locations/flat`

## Home Assistant Git Pull Add-on Setup

## Home Assistant Git Pull Add-on Setup

Based on official Home Assistant Git Pull add-on documentation.

### House NUC Configuration:
```yaml
repository: "https://github.com/etancik/home-automation.git"
git_branch: "ha-config-house"
git_remote: "origin"
auto_restart: true
restart_ignore:
  - ".git/"
  - "deployment/"
  - "README.md"
  - ".gitignore"
git_command: "pull"
git_prune: false
deployment_key: []
deployment_user: ""
deployment_password: ""
deployment_key_protocol: "rsa"
repeat:
  active: true
  interval: 300
```

### Flat NUC Configuration (Future):
```yaml
repository: "https://github.com/etancik/home-automation.git"
git_branch: "ha-config-flat"
git_remote: "origin"
auto_restart: true
restart_ignore:
  - ".git/"
  - "deployment/"
  - "README.md"
  - ".gitignore"
git_command: "pull"
git_prune: false
deployment_key: []
deployment_user: ""
deployment_password: ""
deployment_key_protocol: "rsa"
repeat:
  active: true
  interval: 300
```

### Key Changes from Default:
- `repository`: Your GitHub repository URL
- `git_branch`: Location-specific branch (`ha-config-house` or `ha-config-flat`)
- `auto_restart`: `true` (so HA restarts when config changes)
- `repeat.active`: `true` (automatic polling every 5 minutes)
- `restart_ignore`: Added deployment folder and git files

## Updating Locations

### To update house configuration:
```bash
# Make changes in homeassistant/locations/house/
git add homeassistant/locations/house/
git commit -m "Update house configuration"
git subtree push --prefix=homeassistant/locations/house origin ha-config-house
```

### To update flat configuration:
```bash
# Make changes in homeassistant/locations/flat/
git add homeassistant/locations/flat/
git commit -m "Update flat configuration"
git subtree push --prefix=homeassistant/locations/flat origin ha-config-flat
```

## Safety Notes

- Always test house configuration first before flat deployment
- Keep `current-config/` in `.gitignore` - it contains secrets!
- Check for hardcoded secrets before committing
- Use separate secrets files for each location
- The core packages are shared automatically through includes

## Device Renaming Required

Before deploying to house, rename these devices in Zigbee2MQTT:
- `0x54ef441000edf7c1` → `"Food Storage Sensor"` (will create entities: sensor.food_storage_sensor_*)
- `0xb4e3f9fffea76436` → `"Living Room Light"` ✅ (already correct!)

This ensures the friendly names in `customize.yaml` will work correctly.