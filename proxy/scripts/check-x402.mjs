const DEFAULT_URL = "https://proxy-production-180c.up.railway.app/tools/check_agent_action";
const DEFAULT_BODY = {
  buyer_agent_id: "agent_demo",
  wallet_address: "0x1234567890abcdef1234567890abcdef12345678",
  action_type: "pay_and_call_asp",
  target_asp_id: "asp_new_expensive",
  amount: 25,
  currency: "USDT",
  chain_id: 196,
  endpoint_url: "https://new-asp.example/mcp",
  payload_summary: "Get token research report",
  category: "research",
  asp_completed_orders: 1,
  similar_service_median_usd: 2,
};

const url = process.env.X402_CHECK_URL || process.argv[2] || DEFAULT_URL;

function fail(message) {
  console.error(`x402 check failed: ${message}`);
  process.exit(1);
}

function requireField(condition, message) {
  if (!condition) {
    fail(message);
  }
}

const response = await fetch(url, {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
  body: JSON.stringify(DEFAULT_BODY),
});

requireField(response.status === 402, `expected HTTP 402, got ${response.status}`);

const header = response.headers.get("payment-required");
requireField(header, "missing PAYMENT-REQUIRED header");

let challenge;
try {
  challenge = JSON.parse(Buffer.from(header, "base64").toString("utf8"));
} catch (error) {
  fail(`PAYMENT-REQUIRED is not base64 JSON: ${error.message}`);
}

const accept = challenge.accepts?.[0];
requireField(challenge.x402Version === 2, `expected x402Version 2, got ${challenge.x402Version}`);
requireField(challenge.resource?.url === url, `resource.url mismatch: ${challenge.resource?.url}`);
requireField(challenge.resource?.url?.startsWith("https://"), `resource.url must be HTTPS: ${challenge.resource?.url}`);
requireField(challenge.resource?.mimeType === "application/json", `resource.mimeType mismatch: ${challenge.resource?.mimeType}`);
requireField(accept?.scheme === "exact", `expected exact scheme, got ${accept?.scheme}`);
requireField(accept?.network === "eip155:196", `expected eip155:196, got ${accept?.network}`);
requireField(accept?.payTo?.startsWith("0x"), `invalid payTo: ${accept?.payTo}`);
requireField(typeof accept?.amount === "string" && BigInt(accept.amount) > 0n, `invalid amount: ${accept?.amount}`);
requireField(typeof accept?.asset === "string" && accept.asset.startsWith("0x"), `invalid asset: ${accept?.asset}`);
requireField(Number(accept?.maxTimeoutSeconds) > 0, `invalid maxTimeoutSeconds: ${accept?.maxTimeoutSeconds}`);

console.log("x402 challenge looks valid");
console.log(`resource.url: ${challenge.resource.url}`);
console.log(`network: ${accept.network}`);
console.log(`amount: ${accept.amount}`);
console.log(`asset: ${accept.asset}`);
