---
applyTo: '**'
---

# Home Automation GitOps

## 🚨 CRITICAL SECURITY REQUIREMENTS 🚨

**ALWAYS CHECK BEFORE COMMITTING THAT YOU ARE NOT INCLUDING SENSITIVE FILES!**

❌ **NEVER COMMIT THESE FILES:**
- `device_config*.h` files (contain WiFi credentials!)
- `secrets.yaml` files (contain API keys, passwords)
- Any file with passwords, API keys, or network credentials
- Configuration files with IP addresses or sensitive data

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

## ⚠️ COMMIT MESSAGE VERIFICATION

**ALWAYS verify commit message accurately describes actual code changes before committing!**

Common issues:
- Describing planned changes instead of actual changes
- Copy-pasting old commit messages
- Mentioning removed code as if it's still there
- Not reflecting last-minute modifications

**Process:**
1. Review actual diff: `git diff`
2. Write commit message matching the diff
3. Double-check: Does message match what changed?
4. Then commit and deploy