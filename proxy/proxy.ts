/**
 * AgentShield payment sidecar.
 *
 * This process is deliberately separate from the existing FastAPI app.
 * It sits in front of it, handles the x402 pay-per-call flow, and only
 * forwards a request through once payment has been verified. The Python
 * risk-scoring code in AgentShield is not modified at all.
 *
 *   Buyer Agent -> this proxy (PROXY_PORT) -> FastAPI (UPSTREAM_BASE_URL)
 *
 * Rewritten against the REAL, verified exports of the installed packages:
 *   @okxweb3/x402-core@0.1.0
 *   @okxweb3/x402-evm@0.2.1
 *   @okxweb3/x402-express@0.1.1
 *
 * Verified by extracting the actual .d.ts files from the npm tarballs
 * (not guessed from docs screenshots). Key differences from the earlier
 * draft:
 *   - There is no Proxy.create / Service.create / charge / session / HmacSigner.
 *     Those names do not exist anywhere in these packages.
 *   - The seller side never needs a private key or a signer. The BUYER signs
 *     the payment; the seller only needs a receiving address (payTo) and
 *     OKX API credentials to talk to the facilitator (verify/settle).
 *   - The real building blocks are:
 *       OKXFacilitatorClient   (@okxweb3/x402-core)      - talks to OKX's facilitator
 *       x402ResourceServer     (@okxweb3/x402-core/server) - wraps the facilitator
 *       registerExactEvmScheme (@okxweb3/x402-evm/exact/server) - adds EVM "exact" scheme
 *       paymentMiddleware      (@okxweb3/x402-express)   - the actual Express middleware
 *
 * It protects the listed routes with a paywall, then forwards every request
 * to FastAPI. Routes not listed in the payment config remain free passthrough.
 */

import dotenv from "dotenv";
// Load .env into process.env with explicit API to avoid side-effect-only import
dotenv.config();
import express, { type Request, type Response } from "express";
import { createProxyMiddleware } from "http-proxy-middleware";
import { OKXFacilitatorClient } from "@okxweb3/x402-core";
import { x402ResourceServer, type RoutesConfig } from "@okxweb3/x402-core/server";
import type { Network } from "@okxweb3/x402-core/types";
import { registerExactEvmScheme } from "@okxweb3/x402-evm/exact/server";
import { paymentMiddleware } from "@okxweb3/x402-express";

function requireEnv(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required env var: ${name}. Copy .env.example to .env and fill it in.`);
  }
  return value;
}

// X Layer mainnet chain ID is 196. x402 networks use CAIP-2 format: "eip155:<chainId>".
const CHAIN_ID = Number(process.env.CHAIN_ID ?? "196");
const NETWORK = `eip155:${CHAIN_ID}` as Network;

const SELLER_WALLET_ADDRESS = requireEnv("SELLER_WALLET_ADDRESS"); // public, where payments land
const OKX_API_KEY = requireEnv("OKX_API_KEY");
const OKX_SECRET_KEY = requireEnv("OKX_SECRET_KEY");
const OKX_PASSPHRASE = requireEnv("OKX_PASSPHRASE");
const OKX_BASE_URL = process.env.OKX_BASE_URL ?? "https://web3.okx.com";
const UPSTREAM_BASE_URL = process.env.UPSTREAM_BASE_URL ?? "http://localhost:8000";
const PROXY_PORT = Number(process.env.PROXY_PORT ?? "3000");

// This is FastAPI's internal AGENTSHIELD_API_KEY (see config.py / require_api_key).
// Buyer agents never see or need this -- the proxy holds it and attaches it to
// every forwarded request. External callers authenticate via x402 payment
// instead; this key just keeps FastAPI from being called directly, bypassing
// the paywall.
const UPSTREAM_API_KEY = process.env.UPSTREAM_API_KEY;

// Prices are plain dollar amounts (Money = string | number), e.g. "$0.05" or 0.05.
const PRICE_CHECK_AGENT_ACTION = process.env.PRICE_CHECK_AGENT_ACTION ?? "0.05";
const PRICE_CHECK_PAYMENT_REQUEST = process.env.PRICE_CHECK_PAYMENT_REQUEST ?? "0.05";
const PRICE_CHECK_CONTRACT_PERMISSION = process.env.PRICE_CHECK_CONTRACT_PERMISSION ?? "0.05";
const SYNC_FACILITATOR_ON_START = process.env.SYNC_FACILITATOR_ON_START === "true";
const BYPASS_X402_PAYWALL = process.env.BYPASS_X402_PAYWALL === "true";

// 1. Facilitator client -- talks to OKX's x402 facilitator over HMAC-signed
//    REST calls to verify and settle payments. This replaces the invented
//    "Proxy.create(...)" from the earlier draft. No wallet/private key here.
const facilitatorClient = new OKXFacilitatorClient({
  apiKey: OKX_API_KEY,
  secretKey: OKX_SECRET_KEY,
  passphrase: OKX_PASSPHRASE,
  baseUrl: OKX_BASE_URL,
  // syncSettle: true, // uncomment to wait for on-chain confirmation before responding
});

// 2. Resource server -- combines the facilitator with a payment scheme.
//    registerExactEvmScheme adds the "exact" EVM scheme (pay-exact-amount)
//    for the given network.
const resourceServer = new x402ResourceServer(facilitatorClient);
registerExactEvmScheme(resourceServer, { networks: [NETWORK] });

// 3. Route configuration -- each protected route declares what it accepts.
const routes: RoutesConfig = {
  "POST /tools/check_agent_action": {
    accepts: {
      scheme: "exact",
      payTo: SELLER_WALLET_ADDRESS,
      price: PRICE_CHECK_AGENT_ACTION,
      network: NETWORK,
    },
    description: "AgentShield: general preflight action risk check",
  },
  "POST /tools/check_payment_request": {
    accepts: {
      scheme: "exact",
      payTo: SELLER_WALLET_ADDRESS,
      price: PRICE_CHECK_PAYMENT_REQUEST,
      network: NETWORK,
    },
    description: "AgentShield: payment request sanity check",
  },
  "POST /tools/check_contract_permission": {
    accepts: {
      scheme: "exact",
      payTo: SELLER_WALLET_ADDRESS,
      price: PRICE_CHECK_CONTRACT_PERMISSION,
      network: NETWORK,
    },
    description: "AgentShield: smart contract permission check",
  },
  // check_asp_risk, /health, /mcp, /demo are intentionally NOT listed here,
  // so paymentMiddleware leaves them unprotected/free -- it only guards
  // routes it's explicitly told about.
};

const app = express();
app.use(express.json());

// 4. Attach the x402 paywall to the listed routes only.
//
// Local development often needs to test the reverse-proxy behavior without
// depending on the remote OKX facilitator. Keep this false in production.
if (!BYPASS_X402_PAYWALL) {
  app.use(paymentMiddleware(routes, resourceServer, undefined, undefined, SYNC_FACILITATOR_ON_START));
}

// 5. Forward everything (paid-and-passed, and free routes) to FastAPI.
//
//    Two fixes over a naive createProxyMiddleware() call:
//
//    a) express.json() above already consumed the request stream to
//       populate req.body. http-proxy-middleware forwards the raw
//       stream by default, so without re-writing it, FastAPI would
//       receive an empty body. We re-serialize req.body back onto the
//       outgoing request in onProxyReq, after fixing Content-Length.
//
//    b) FastAPI's require_api_key dependency expects an X-API-Key header
//       matching AGENTSHIELD_API_KEY. Buyer agents authenticate via x402
//       payment, not this key -- so the proxy attaches it itself here,
//       rather than requiring external callers to know an internal secret.
app.use(
  "/",
  createProxyMiddleware({
    target: UPSTREAM_BASE_URL,
    changeOrigin: true,
    on: {
      proxyReq: (proxyReq, req) => {
        if (UPSTREAM_API_KEY) {
          proxyReq.setHeader("X-API-Key", UPSTREAM_API_KEY);
        }

        const body = (req as Request).body;
        const hasBody = body && Object.keys(body).length > 0;
        if (hasBody) {
          const payload = JSON.stringify(body);
          proxyReq.setHeader("Content-Type", "application/json");
          proxyReq.setHeader("Content-Length", Buffer.byteLength(payload));
          proxyReq.write(payload);
        }
      },
    },
  })
);

app.listen(PROXY_PORT, () => {
  console.log(`AgentShield payment proxy listening on :${PROXY_PORT}`);
  console.log(`Network: ${NETWORK}`);
  console.log(`OKX facilitator: ${OKX_BASE_URL}`);
  console.log(`Sync facilitator on start: ${SYNC_FACILITATOR_ON_START}`);
  console.log(`Bypass x402 paywall: ${BYPASS_X402_PAYWALL}`);
  console.log(`Forwarding paid/free requests to ${UPSTREAM_BASE_URL}`);
});
