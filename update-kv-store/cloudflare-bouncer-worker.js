/**
 * This worker reads from a KV key that contains the Crowdstrike CAPI
 * blocklist. This must be added as a bindning to the worker. 
 */

let cachedSet = null;
let lastUpdate = 0;

export default {
  async fetch(request, env, ctx) {
    const visitorIP = request.headers.get("cf-connecting-ip");

    // 1. Safety First: Allowlist
    const allowlist = ["YOUR-FIXED-IP", "ANOTHER-IP"]; 
    if (allowlist.includes(visitorIP)) return fetch(request);

    try {
      const now = Date.now();
      // Re-sync from KV every 5 minutes (300,000 ms)
      if (!cachedSet || (now - lastUpdate > 300000)) {
        
        // This gets the string: {"metadata":{}, "value":"[...]"}
        // You need to use the bindning name you setup in Cloudflare
        const rawEnvelope = await env.CS_BLOCKLIST_BINDING.get("CS_CAPI_LIST");
        
        if (rawEnvelope) {
          const envelope = JSON.parse(rawEnvelope);
          
          // The SDK puts your actual IP array string inside the 'value' property
          // We need to parse that inner string to get the actual Array
          const ipArray = JSON.parse(envelope.value);
          
          cachedSet = new Set(ipArray);
          lastUpdate = now;
          console.log(`Bouncer active: ${cachedSet.size} IPs loaded.`);
        }
      }

      // 2. High-speed lookup
      if (cachedSet && cachedSet.has(visitorIP)) {
        const hostname = request.headers.get("host") || new URL(request.url).hostname;
        console.log(`Blocked IP: ${visitorIP} trying to reach: ${hostname}`);
        return new Response("Forbidden: IP blacklisted by CrowdSec", { status: 403 });
      }

    } catch (err) {
      // If anything fails (parsing, network, etc.), fail open
      console.error("Worker Error:", err);
      return fetch(request);
    }

    return fetch(request);
  }
};