# Troubleshooting Guide

This document helps you diagnose and resolve common issues with the ComfoClime Home Assistant integration.

## Table of Contents
- [GitHub Integration Timeout Errors](#github-integration-timeout-errors)
- [Connection Issues](#connection-issues)
- [Entity Not Updating](#entity-not-updating)
- [Integration Not Loading](#integration-not-loading)

## GitHub Integration Timeout Errors

### Symptoms
You see errors like:
```
Logger: homeassistant.components.github
An error occurred while processing new events - Timeout of 20 reached while waiting for https://api.github.com/repos/...
```

### Diagnosis
**This is NOT a ComfoClime integration issue.** These errors come from Home Assistant's built-in GitHub integration, which is a separate integration that monitors GitHub repositories for updates.

### Root Cause
You have configured the GitHub integration in Home Assistant to monitor repositories, and it's experiencing timeout issues connecting to GitHub's API. This can happen due to:
- Network connectivity issues
- GitHub API rate limiting
- Slow internet connection
- Firewall blocking GitHub API access

### Solutions

1. **Disable the GitHub integration** (if you don't need it):
   - Go to Settings → Devices & Services
   - Find "GitHub" integration
   - Click the three dots menu → Delete

2. **Increase the timeout** (if you want to keep the integration):
   - The GitHub integration timeout is controlled by Home Assistant core
   - Check your network connectivity to github.com
   - Consider using a GitHub Personal Access Token if you're hitting rate limits

3. **Suppress log warnings** (development only):
   - Edit `.devcontainer/configuration.yaml` and add:
   ```yaml
   logger:
     logs:
       homeassistant.components.github: error
   ```

### Important Notes
- The ComfoClime integration does **not** use or depend on the GitHub integration
- These timeout errors **do not affect** ComfoClime functionality
- ComfoClime operates entirely on your local network and doesn't communicate with GitHub

---

## Connection Issues

### Symptoms
- Integration fails to setup
- "Could not connect to ComfoClime device" error
- Entities showing "Unavailable"

### Diagnosis
The integration cannot communicate with your ComfoClime device.

### Solutions

1. **Verify network connectivity**:
   ```bash
   curl http://YOUR_COMFOCLIME_IP/api/dashboard
   ```
   You should get a JSON response with device data.

2. **Check IP address**:
   - Make sure you're using the correct IP address
   - The device IP might have changed (use your router's DHCP leases)
   - Consider setting a static IP for your ComfoClime device

3. **Check firewall**:
   - Ensure Home Assistant can reach the ComfoClime device
   - Check both Home Assistant's and your network's firewall rules

4. **Verify device is powered on**:
   - The ComfoClime device must be powered on and connected to your network

---

## Entity Not Updating

### Symptoms
- Entity values are stale
- Last updated timestamp is old
- Entities show "Unknown" or "Unavailable"

### Diagnosis
The coordinator is not fetching new data from the device.

### Solutions

1. **Check polling interval**:
   - Go to Settings → Devices & Services → ComfoClime → Configure
   - Verify polling interval (default: 60 seconds)

2. **Reload the integration**:
   - Settings → Devices & Services → ComfoClime
   - Click the three dots → Reload

3. **Check logs**:
   - Settings → System → Logs
   - Look for errors related to "comfoclime"

4. **Verify device connectivity**:
   - Test connection with curl (see Connection Issues above)

---

## Integration Not Loading

### Symptoms
- ComfoClime doesn't appear in Devices & Services
- Error during integration setup
- "Failed to initialize" errors in logs

### Diagnosis
The integration failed to load or initialize.

### Solutions

1. **Check Home Assistant version**:
   - Minimum required version: 2023.x or later
   - Update Home Assistant if needed

2. **Verify installation**:
   - For HACS: Check that the integration is properly installed
   - For manual: Verify files are in `custom_components/comfoclime/`

3. **Check manifest.json**:
   - Ensure `manifest.json` is valid and not corrupted
   - Verify required dependencies (aiohttp) are available

4. **Clear cache and restart**:
   ```bash
   # From Home Assistant container/terminal:
   rm -rf /config/.storage/core.restore_state
   ha core restart
   ```

5. **Check logs for details**:
   - Enable debug logging in `configuration.yaml`:
   ```yaml
   logger:
     logs:
       custom_components.comfoclime: debug
   ```

---

## Getting Help

If you've tried the solutions above and still experience issues:

1. **Check existing issues**: [GitHub Issues](https://github.com/Revilo91/comfoclime/issues)
2. **Gather diagnostic information**:
   - Home Assistant version
   - ComfoClime integration version
   - Relevant log entries (with debug logging enabled)
   - Device model and firmware version
3. **Create a new issue** with:
   - Clear description of the problem
   - Steps to reproduce
   - Diagnostic information from step 2
   - What you've already tried

---

## Development Issues

### Dev Container: Port 8123 Not Reachable

**Solution**: 
- Check the PORTS tab in VS Code
- Verify port forwarding is active
- Try `http://localhost:8123` directly

### Dev Container: Integration Not Loading

**Solution**:
- Verify symbolic link: `ls -la /config/custom_components/comfoclime`
- Restart container: `container restart`
- Check setup script ran: `bash .devcontainer/setup.sh`

### Dev Container: Changes Not Applied

**Solution**:
- Always restart after code changes: `container restart`
- Verify you're editing files in `/workspaces/comfoclime/`
- Not in `/config/custom_components/` (that's just a symlink)
