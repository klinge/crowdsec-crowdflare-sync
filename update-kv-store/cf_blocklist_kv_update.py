import json
import logging
import os
import subprocess
import sys
from dotenv import load_dotenv
from cloudflare import Cloudflare


# Load the .env file
load_dotenv()
CF_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
CF_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CF_LIST_ID = os.getenv("CLOUDFLARE_LIST_ID", "")
CF_LIST_NAME = os.getenv("CLOUDFLARE_LIST_NAME", "")
KV_NAMESPACE_ID = os.getenv("KV_NAMESPACE_ID", "")
KV_KEY_NAME = os.getenv("KV_KEY_NAME", "")

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cf-list-update')

# Suppress verbose logging from dependencies
logging.getLogger('cloudflare').setLevel(logging.INFO)
logging.getLogger('httpx').setLevel(logging.INFO)
logging.getLogger('httpcore').setLevel(logging.INFO)

# Exit if required env vars are missing
if not CF_ACCOUNT_ID or not CF_API_TOKEN or not KV_NAMESPACE_ID or not KV_KEY_NAME:
    logger.error("Missing required environment variables for Cloudflare configuration.")
    sys.exit(1)


def get_crowdsec_ips():
    """Fetch banned IPs from CrowdSec Community API.

    Executes 'cscli decisions list' to retrieve CAPI decisions and formats
    them for Cloudflare IP list consumption.

    Returns:
        list: List of IPs.
              Returns empty list on error.

    Raises:
        Logs errors but doesn't raise exceptions to allow graceful handling.

    Note:
        Requires root privileges to execute cscli command.
    """
    try:
        output = subprocess.check_output([
            "cscli", "decisions", "list", "-a",
            "--origin", "CAPI", "-o", "json"])
        result = json.loads(output)

        # Handle both single object and array of objects
        all_decisions = []
        if isinstance(result, list):
            for item in result:
                all_decisions.extend(item.get('decisions', []))
        else:
            all_decisions = result.get('decisions', [])

        logger.debug(f"IPs in cscli output {len(all_decisions)}")
        # Extract only the IP values
        # CrowdSec decisions can be for IPs or Ranges (Subnets)
        ips = [d['value'] for d in all_decisions if d['scope'] == 'Ip' or d['scope'] == 'Range']
        logger.debug(f"IPs to sync: {ips}")
        logger.info(f"Fetched {len(ips)} CAPI blocklist IPs")
        return list(set(ips))  # Deduplicate
    except Exception as e:
        logger.error(f"Error fetching CrowdSec data: {e}")
        return []


def sync_to_cloudflare():
    # 1. Initialize the Cloudflare Client
    client = Cloudflare(api_token=CF_API_TOKEN)

    # 2. Get the IP list
    ip_list = get_crowdsec_ips()
    if not ip_list:
        logger.error("No IPs found to sync. Skipping.")
        return

    # 3. Use the SDK to update the KV value
    # In the modern SDK, the value must be a string (hence json.dumps)
    try:
        logger.info(f"Updating KV key '{KV_KEY_NAME}' with {len(ip_list)} IPs...")
        client.kv.namespaces.values.update(
            key_name=KV_KEY_NAME,
            account_id=CF_ACCOUNT_ID,
            namespace_id=KV_NAMESPACE_ID,
            value=json.dumps(ip_list),
            metadata=""
        )
        print(f"Successfully updated '{KV_KEY_NAME}' at the CF edge.")
    except Exception as e:
        print(f"Cloudflare SDK Error: {e}")


if __name__ == "__main__":
    sync_to_cloudflare()
