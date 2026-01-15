# Crowdsec to Cloudflare Sync

Automatically sync Crowdsec threat intelligence to Cloudflare. 

## Overview

Crowdsec has two bouncers for Cloudflare. The original one is deprecated due to new Cloudflare API rate 
limits. The Worker based bouncer is complex and not very suitable for a free Cloudflare plan.

Using both Crowdsec and Cloudflare I still wanted the advantage of being able to off-load some of the blocking from 
my local server to the edge servers on Cloudflare. So this project contains two small python scripts 
that cover my main needs. 

1. **update_blocklist**: contains a script that pulls data from the Crowdsec community blocklist (CAPI) and updates
a Cloudflare IP filter list
2. **update-waf-rules** contains a script that lists locally banned IPs from the Crowdsec engine on your server 
and updates a Cloudflare WAF ruleset 

To respect Cloudflare API rate limits they're made to be scheduled at fixed intervals - not 
run in real-time. 

## Features

- **Cloudflare integration** - Updates IP lists/rules via API
- **Systemd service** - Prepared to run as automated system service
- **Comprehensive logging** - Full audit trail for operations, logs to system log when scheduled
- **Low complexity** - The scripts are kept simple to make them easy to follow and adjust

## Scripts

Each script has its own README with detailed setup and usage instructions:

- [update_blocklist](https://github.com/klinge/crowdsec-crowdflare-sync/tree/main/update-blocklist) - Sync CAPI community blocklist to Cloudflare IP List
- [update-waf-rules](https://github.com/klinge/crowdsec-crowdflare-sync/tree/main/update-waf-rules) - Sync local CrowdSec decisions to Cloudflare WAF rule

## Requirements

- CrowdSec installed (with CAPI enabled for update_blocklist)
- Cloudflare account with a valid API token
- Existing Cloudflare IP List and/or WAF rule (scripts don't create them)
- Python 3.7+
- Root access (required for `cscli` command)

## Cloudflare API token permissions
The Cloudflare API token you use need these permissions: 

- Account: 
  - Account Rulesets:Edit, Account Filter Lists:Edit, Account Firewall Access Rules:Edit
- For the relevant zone
  - Zone:Read, Firewall Services:Edit

## Quick Start

Clone the repo into an empty folder: 
```bash
git clone https://github.com/yourusername/crowdsec-cloudflare-sync.git
```

1. Create a virtual environment and activate it
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env-EDITME` to .env and configure with your values (see [SETUP.md](SETUP.md) for help finding Cloudflare IDs)
4. Test with `--dry-run` flag first
5. Schedule with systemd or cron (recommended: every 2+ hours) or another scheduling tool your OS supports

## Deployment

In the "deploy" directory you find examples of systemd unit files and timers that you can use if 
you are on linux. If you want to use cron or are on another OS you are on your own. 

## Warnings

- Tested on Linux only - other OSes should work but are not verified
- Will overwrite existing Cloudflare firewall rules - be safe and backup first
- Doesn't handle Cloudflare API rate limiting - don't run too frequently (max every 2 hours)
- Always test with `--dry-run` before production use 

## Contributing
Feel free to fork the repository and make a pull request. Test with --dry-run before submitting. 

## License

MIT License