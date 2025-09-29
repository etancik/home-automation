# House Manual Setup Instructions

After the Git Pull add-on successfully deploys the configuration, you need to manually create the secrets.yaml file.

## Required: Create secrets.yaml

1. **Connect to your House NUC** (SSH or Home Assistant terminal add-on)

2. **Create secrets.yaml** in the /config directory:
   ```bash
   nano /config/secrets.yaml
   ```

3. **Copy this template and customize with your coordinates**:
   ```yaml
   # House Location Secrets - Replace with your actual location
   house_latitude: YOUR_LATITUDE_HERE
   house_longitude: YOUR_LONGITUDE_HERE
   house_elevation: YOUR_ELEVATION_HERE
   ```

4. **Save the file** (Ctrl+O, Ctrl+X in nano)

5. **Restart Home Assistant** or run Git Pull add-on again

## Why This is Needed

The configuration references `!secret house_latitude` etc., but Home Assistant expects these values to exist in secrets.yaml. Without this file, HA will show the onboarding wizard.

## After Setup

Once secrets.yaml exists:
- ✅ No onboarding wizard  
- ✅ Your house location will be properly set
- ✅ All sensors and automations will work
- ✅ Git Pull add-on will update configuration automatically