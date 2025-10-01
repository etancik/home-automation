---
applyTo: '**'
---

# Home Automation GitOps

## Deployment Branches
- `ha-config-house` ← `homeassistant/locations/house/`
- `ha-config-flat` ← `homeassistant/locations/flat/`

## Deploy Commands
```bash
# House
git subtree push --prefix=homeassistant/locations/house origin ha-config-house

# Flat  
git subtree push --prefix=homeassistant/locations/flat origin ha-config-flat

# If "Everything up-to-date" error:
git subtree split --prefix=homeassistant/locations/house -b temp
git push origin temp:ha-config-house
git branch -D temp
```

## Workflow
1. Edit `homeassistant/locations/{location}/`
2. Commit to master
3. Deploy with `git subtree push`
4. Home Assistant auto-syncs via Git Pull add-on