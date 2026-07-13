# AgentShield Payment Proxy

A small Node/TypeScript sidecar that adds Onchain OS x402 pay-per-call
charging in front of the existing AgentShield FastAPI service, with **no
changes to the Python code**.

```
Buyer Agent -> this proxy (:3000) -> FastAPI AgentShield (:8000, unchanged)
```

Unpaid requests never reach your Python code: the proxy returns HTTP 402
and stops there. Only verified, paid requests get forwarded.

## 1. Prerequisites

- Node.js 20+
- Your existing AgentShield FastAPI service already runnable locally
  (`uv run uvicorn app.main:app --reload`, per the main repo's README)
- An EVM-compatible wallet address used to receive payments
- OKX API credentials from the Developer Portal (API key / secret / passphrase)

## 2. Install dependencies

```bash
cd proxy
npm install
```

## 3. Configure environment

```bash
cp .env.example .env
```

Fill in `.env` with your real values. Never commit this file or paste its
contents anywhere.

Set `UPSTREAM_API_KEY` to the same value as the FastAPI app's
`AGENTSHIELD_API_KEY` if you enable API-key protection on the upstream
service.

`OKX_BASE_URL` defaults to `https://web3.okx.com`. Keep
`SYNC_FACILITATOR_ON_START=false` for local development if your network cannot
reach the OKX facilitator consistently; set it to `true` in production so
startup fails early when payment settlement is unavailable.

For local proxy-forwarding tests without OKX payment verification, set
`BYPASS_X402_PAYWALL=true`. Keep it `false` in production.

## 4. Run both services

Terminal 1 -- your existing FastAPI app, unchanged:

```bash
uv run uvicorn app.main:app --reload
```

Terminal 2 -- the payment proxy:

```bash
cd proxy
npm run dev
```

If your network requires an HTTP(S) proxy to reach `https://web3.okx.com`, set
`HTTPS_PROXY`/`HTTP_PROXY` in your shell and run:

```bash
npm run dev:env-proxy
```

## 5. Test end-to-end

1. Call `POST http://localhost:3000/tools/check_agent_action` with a normal
   AgentShield payload and no payment credential attached.
2. Confirm you get back HTTP 402 with payment details (amount, recipient,
   token) -- this proves unpaid requests are being stopped before they
   reach your Python code.
3. Using a test wallet, sign and attach the payment credential per the
   docs' "Verify on testnet" section, then retry the same request.
4. Confirm you now get back a normal AgentShield decision response
   (`decision`, `risk_score`, `summary`, etc.) -- this proves the paid
   path forwards correctly to FastAPI and back.
5. Repeat once for `check_payment_request` and `check_contract_permission`.
6. Confirm `check_asp_risk` still answers immediately with no payment
   required, since it's configured as free passthrough.

Do all of this on testnet with test funds before pointing the proxy at a
production receiving wallet.

## 6. Deploy

Run both processes on your actual host (not localhost) so OKX's listing
review and hackathon judges can reach the proxy's public URL. Point
`UPSTREAM_BASE_URL` at wherever the FastAPI container ends up living --
if both run on the same machine, `http://localhost:8000` is fine as long
as only the proxy's port is exposed publicly.
