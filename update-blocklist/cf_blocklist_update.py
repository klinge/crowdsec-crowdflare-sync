import os
import sys
import argparse
import subprocess
import json
import logging
from dotenv import load_dotenv
from cloudflare import Cloudflare

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cloudflare-list-sync')


# Load the .env file
load_dotenv()
CF_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
CF_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CF_LIST_ID = os.getenv("CLOUDFLARE_LIST_ID", "")
CF_LIST_NAME = os.getenv("CLOUDFLARE_LIST_NAME", "")

# Exit if required env vars are missing
if not CF_ACCOUNT_ID or not CF_API_TOKEN or not CF_LIST_ID or not CF_LIST_NAME:
    logger.error("Missing required environment variables for Cloudflare configuration.")
    sys.exit(1)

# Configure Cloudflare Client
client = Cloudflare(
    api_token=CF_API_TOKEN,
)


def prioritize_ips(ips, limit=9900):
    """Prioritize IPs by threat level for Cloudflare list limits.

    Sorts IPs by severity: exploits > bruteforce > scans, ensuring the most
    critical threats are included when truncating to Cloudflare's limits.

    Args:
        ips (list): List of IP dictionaries with 'ip' and 'comment' keys
        limit (int): Maximum number of IPs to return (default: 9800)

    Returns:
        list: Prioritized list of IP dictionaries, truncated to limit

    Example:
        >>> ips = [{'ip': '1.2.3.4', 'comment': 'CrowdSec CAPI: http:exploit'}]
        >>> prioritized = prioritize_ips(ips, 1000)
    """
    if len(ips) <= limit:
        return ips

    # Separate by scenario type
    exploits = [ip for ip in ips if 'http:exploit' in ip['comment']]
    bruteforce = [ip for ip in ips if 'http:bruteforce' in ip['comment']]
    scans = [ip for ip in ips if 'http:scan' in ip['comment']]

    logger.debug(
        f"Found {len(exploits)} exploits, {len(bruteforce)} bruteforce, {len(scans)} scans"
    )

    # Build prioritized list
    prioritized = []
    prioritized.extend(exploits[:limit])  # Add all exploits first

    remaining = limit - len(prioritized)
    if remaining > 0:
        prioritized.extend(bruteforce[:remaining])  # Then bruteforce

    remaining = limit - len(prioritized)
    if remaining > 0:
        prioritized.extend(scans[:remaining])  # Finally scans

    logger.info(f"Prioritized to {len(prioritized)} IPs (exploits first)")
    return prioritized


def get_crowdsec_ips():
    """Fetch banned IPs from CrowdSec Community API.

    Executes 'cscli decisions list' to retrieve CAPI decisions and formats
    them for Cloudflare IP list consumption.

    Returns:
        list: List of IP dictionaries with 'ip' and 'comment' keys.
              Returns empty list on error.

    Raises:
        Logs errors but doesn't raise exceptions to allow graceful handling.

    Note:
        Requires root privileges to execute cscli command.
    """
    try:
        logger.info("Fetching CrowdSec CAPI decisions")
        output = subprocess.check_output(["cscli", "decisions", "list", "-a", "--origin", "CAPI", "-o", "json"])
        decisions = json.loads(output)

        ips_to_sync = []
        for item in decisions:
            for d in item.get('decisions', []):
                ips_to_sync.append({
                    "ip": d.get('value'),
                    "comment": f"CrowdSec CAPI: {d.get('scenario')}"
                })

        logger.info(f"Found {len(ips_to_sync)} CAPI IPs")
        return ips_to_sync
    except Exception as e:
        logger.error(f"Error fetching CrowdSec data: {e}")
        return []


def run_sync(dry_run) -> None:
    """Main synchronization function.

    Orchestrates the complete sync process:
    1. Verifies Cloudflare list name matches configuration
    2. Fetches CrowdSec CAPI decisions
    3. Prioritizes IPs by threat level
    4. Updates Cloudflare IP list

    Returns:
        None: Function exits early on errors or validation failures

    Raises:
        Logs errors and exits on failures to ensure safe operation.
    """
    logger.info("Starting Cloudflare sync")

    # Fetch existing list to verify name
    try:
        list = client.rules.lists.get(
            list_id=CF_LIST_ID,
            account_id=CF_ACCOUNT_ID,
        )
        if list.name != CF_LIST_NAME:
            logger.warning("Listname not matching expected name, aborting sync")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Cloudflare API Error: {e}")
        sys.exit(1)

    # Fetch IPs from CrowdSec
    ips = get_crowdsec_ips()
    if not ips:
        logger.warning("No IPs found to sync")
        sys.exit(1)

    # Prioritize IPs according to threat level
    prioritized_ips = prioritize_ips(ips)

    # Update Cloudflare list
    if dry_run:
        logger.info("--- DRYRUN: Not sent to Cloudflare ---")
        logger.info(
            f"Would sync {len(prioritized_ips)} IPs to Cloudflare list {CF_LIST_NAME} ({CF_LIST_ID})"
        )
        logger.info("--- END DRYRUN ---")
    else:
        try:
            result = client.rules.lists.items.update(
                account_id=CF_ACCOUNT_ID,
                list_id=CF_LIST_ID,
                body=prioritized_ips
            )
            logger.info(
                f"Successfully synced {len(prioritized_ips)} IPs. Operation ID: {result.operation_id}"
            )
        except Exception as e:
            logger.error(f"Cloudflare API Error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update Cloudflare list with Crowdsec community blocklist (CAPI)."
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Write out what would be sent to Cloudflare, but make no changes.'
    )
    args = parser.parse_args()
    run_sync(args.dry_run)
