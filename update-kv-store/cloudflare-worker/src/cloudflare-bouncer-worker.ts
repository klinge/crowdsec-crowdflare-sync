/**
 * This worker reads from a KV key that contains the Crowdstrike CAPI
 * blocklist. This must be added as a bindning to the worker. 
 */

interface Env {
  CS_BLOCKLIST_BINDING: KVNamespace;
}

let cachedSet: Set<string> | null = null;
let lastUpdate: number = 0;

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const visitorIP: string | null = request.headers.get("cf-connecting-ip");

    // If no visitor IP, allow the request
    if (!visitorIP) return fetch(request);

    // 1. Safety First: Allowlist
    const allowlist: string[] = ["YOUR-FIXED-IP", "ANOTHER-IP"]; 
    if (allowlist.includes(visitorIP)) return fetch(request);

    try {
      const now: number = Date.now();
      // Re-sync from KV every 5 minutes (300 000 ms)
      if (!cachedSet || (now - lastUpdate > 300000)) {
        
        // This gets the string: {"metadata":{}, "value":"[...]"}
        // You need to use the bindning name you setup in Cloudflare
        const rawEnvelope: string | null = await env.CS_BLOCKLIST_BINDING.get("CS_CAPI_LIST", 
        {
          type: "text",           // avoid unnecessary JSON parse here
          cacheTtl: 600           // seconds — let edge cache the raw KV value longer
        });
        
        if (rawEnvelope) {
          const envelope = JSON.parse(rawEnvelope);
          
          // The SDK puts your actual IP array string inside the 'value' property
          // We need to parse that inner string to get the actual Array
          const ipArray: string[] = JSON.parse(envelope.value);
          
          cachedSet = new Set(ipArray);
          lastUpdate = now;
          console.log(`Blocklist refreshed: ${cachedSet.size} IPs loaded.`);
        }
      }

      // 2. High-speed lookup
      if (cachedSet && cachedSet.has(visitorIP)) {
        const hostname: string = request.headers.get("host") || new URL(request.url).hostname;
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
} satisfies ExportedHandler<Env>;