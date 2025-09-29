# House Deployment Notes

## Required Manual Setup

After Git Pull deployment, you MUST create a `secrets.yaml` file manually on the House NUC with:

```yaml
# House location coordinates (replace with your actual coordinates)
house_latitude: 50.0755
house_longitude: 14.4378  
house_elevation: 399
```

## Steps:

1. **SSH into House NUC** or use Home Assistant File Editor add-on
2. **Create `/config/secrets.yaml`** with your actual coordinates
3. **Restart Home Assistant** after creating secrets.yaml

## Why this is needed:

The configuration references `!secret house_latitude` etc., so Home Assistant needs the secrets.yaml file to complete the setup and avoid the onboarding wizard.

## Security Note:

Never commit secrets.yaml to Git! It's already in .gitignore for safety.