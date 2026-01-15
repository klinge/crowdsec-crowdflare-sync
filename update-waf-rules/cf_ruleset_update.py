import os
import argparse
import subprocess
import json
import sys
import logging
from dotenv import load_dotenv
from cloudflare import Cloudflare


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('cf-ruleset-update')

# Load the .env file
load_dotenv()
CF_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID", "")
CF_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN", "")
CF_ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID", "")
CF_RULESET_ID = os.getenv("CLOUDFLARE_RULESET_ID", "")
CF_RULE_ID = os.getenv("CLOUDFLARE_RULE_ID", "")

# Exit if necessary env vars are missing
if not CF_ACCOUNT_ID or not CF_API_TOKEN or not CF_RULESET_ID or not CF_RULE_ID or not CF_ZONE_ID:
    logger.error("Missing required environment variables for Cloudflare configuration.")
    sys.exit(1)

# Configure Cloudflare Client
client = Cloudflare(
    api_token=CF_API_TOKEN,
)


def get_crowdsec_banned_ips() -> list:
    """Fetching current banned IPs from CrowdSec using cscli"""
    try:
        data = subprocess.check_output(["cscli", "decisions", "list", "-o", "json"])
        result = json.loads(data)
        # Get all IPs from decisions filter on type=ban
        # The ip is in the "value" field of the decision dict
        ips = [d["value"] for item in result for d in item.get("decisions", []) if d.get("type") == "ban"]
        return sorted(set(ips))
    except Exception as e:
        logger.error(f"Error fetching IPs from CrowdSec: {e}")
        sys.exit(1)


def format_ip_for_cloudflare(ips) -> str:
    """Format IP address for Cloudflare WAF expression"""
    # Expected format: (ip.src in {91.92.243.241 195.178.110.68})
    ip_string = " ".join(ips)

    return f"(ip.src in {{{ip_string}}})"


def fetch_current_rule():
    """Fetch the current rule from Cloudflare ruleset"""
    try:
        ruleset = client.rulesets.get(
            ruleset_id=CF_RULESET_ID,
            zone_id=CF_ZONE_ID,
        )
        rule = next((rule for rule in ruleset.rules if rule.id == CF_RULE_ID), None)
    except Exception as e:
        logger.error(f"Error fetching ruleset: {e}")
        sys.exit(1)

    # Verify that rule is found - else exit
    if rule is None:
        logger.error(f"Rule with ID {CF_RULE_ID} not found in ruleset")
        sys.exit(1)

    return rule


def run_sync(dry_run) -> None:
    logger.info("Starting Cloudflare ruleset update.")

    # 1. Fetch IP list from CrowdSec
    ip_list = get_crowdsec_banned_ips()
    logger.info(f"Fetched {len(ip_list)} IP-adresses from CrowdSec.")

    # 2. Format ips to correct expression format for cloudflare
    new_expression = format_ip_for_cloudflare(ip_list)

    # 3. Fetch existing ruleset from Cloudflare
    rule = fetch_current_rule()
    if rule is None:
        logger.error(f"Rule with ID {CF_RULE_ID} not found in ruleset")
        sys.exit(1)

    # 5. Dry run or update Cloudflare
    if dry_run:
        logger.info("--- DRYRUN: Not sent to Cloudflare ---")
        logger.info(f"New expression would be: {new_expression}")
        logger.info(f"Current expression is: {rule.expression}")
        logger.info(f'Current rule version is: {rule.version}')
        logger.info("--- END DRYRUN: No changes made to Cloudflare ruleset.")
    else:
        try:
            response = client.rulesets.rules.edit(
                rule_id=CF_RULE_ID,
                ruleset_id=CF_RULESET_ID,
                zone_id=CF_ZONE_ID,
                id=rule.id or "",
                description=rule.description or "",
                action=rule.action,  # pyright: ignore[reportArgumentType]
                expression=new_expression,
            )  # type: ignore
            logger.info(f"Cloudflare response: {response}")
            logger.info(f"Successfully updated Cloudflare ruleset with {len(ip_list)} IP-adresses.")
        except Exception as e:
            logger.error(f"Error updating Cloudflare ruleset: {e}")
            sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update Cloudflare ruleset with CrowdSec locally banned IP-adresses."
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Write out what would be sent to Cloudflare, but make no changes.'
    )
    args = parser.parse_args()
    run_sync(args.dry_run)
