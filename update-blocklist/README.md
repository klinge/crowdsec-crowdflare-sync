# CrowdSec to Cloudflare IP Sync

Automatically sync CrowdSec Community API (CAPI) blocked IPs to Cloudflare IP lists for edge-level protection.

## Overview

This service fetches threat intelligence from CrowdSec's Community API and updates a Cloudflare IP list to block malicious traffic at the edge. It prioritizes high-severity threats (exploits > bruteforce > scans) and handles Cloudflare's 10,000 item limit by selecting the most critical IPs.

**NOTE**: due to the Cloudflares limit on list length the script does not send the entire CAPI list to Cloudflare. You will not
get the full protection that the list offers. 

## Features

- **Intelligent prioritization** - Exploits get priority over scans
- **Cloudflare integration** - Updates IP lists via API
- **Systemd service** - Runs as automated system service
- **Comprehensive logging** - Full audit trail for operations
- **Safety checks** - Verifies list names before updates

## Requirements

- CrowdSec installed with CAPI enabled
- Cloudflare account with API access
- An existing Cloudflare IP List - the script doesn't create it
- Python 3.7+
- Root access (for cscli command)

## Installation

1. **Clone and setup:**
Suggested location for a unix server setup: 

   ```bash
   sudo mkdir -p /opt/cloudflare-sync
   sudo cp -r * /opt/cloudflare-sync/
   cd /opt/cloudflare-sync
   ```

2. **Create virtual environment:**
   ```bash
   sudo python3 -m venv venv
   sudo venv/bin/pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   sudo cp .env-EDITME .env
   sudo nano .env  # Add your Cloudflare credentials
   sudo chmod 600 .env
   ```

4. **Create systemd service:**
Run with a systemd service + timer. Or use cron if you want. 
Remember cscli, which is used by the script, needs to be run as root. 

## Configuration

### Environment Variables (.env)
Don't forget to change the name of .env-EDITME to .env and
update all the settings in the file with your information. 

## Usage

### Manual execution:
```bash
cd /opt/cloudflare-sync
sudo venv/bin/python cloudflare_update.py
```

### Service management:
```bash
sudo systemctl status cloudflare-list-sync.timer
sudo systemctl start cloudflare-list-sync.service
```

## How it works

1. **Fetch** - Retrieves CAPI decisions from CrowdSec
2. **Prioritize** - Sorts by threat level (exploit > bruteforce > scan)
3. **Limit** - Truncates to 9,800 IPs for Cloudflare limits
4. **Verify** - Checks list name matches configuration
5. **Update** - Replaces entire Cloudflare IP list

## Monitoring

View logs:
```bash
journalctl -u cloudflare-list-sync.service --since today
```

Check timer status:
```bash
systemctl list-timers cloudflare-list-sync.timer
```

## Troubleshooting

- **Permission errors**: Ensure script runs as root for cscli access
- **API errors**: Verify Cloudflare credentials and that API token has list edit permissions
- **No IPs found**: Check CrowdSec CAPI enrollment status
- **No traffic dropped**: For the list to be effective you need a Cloudflare WAF Rule that uses it to drop traffic