# AgentShield

AgentShield is a preflight trust, risk, and spend-control firewall for autonomous agents using OKX.AI Agent Service Providers.

Before an agent pays, calls, hires, approves, signs, or shares sensitive data, AgentShield returns a clear decision:

```text
GO / CAUTION / NO-GO
```

## OKX.AI Genesis Hackathon Fit

AgentShield is built for the OKX.AI Genesis ASP hackathon and the X Layer agent-commerce ecosystem.

- Category: Software Utility / Finance Copilot
- Service mode: A2MCP for standard checks, A2A for custom policy and incident reviews
- Core value: safer agent-to-agent commerce before funds, permissions, or private data move
- Demo target: a buyer agent checks risky and safe ASP interactions before payment

## Problem

Agentic commerce creates a new failure mode: autonomous agents may pay unknown services, accept inflated quotes, approve dangerous transactions, or leak sensitive metadata without human review.

Wallet scanners look mostly at tokens and addresses. AgentShield focuses on the agent-commerce decision:

> Should this agent trust, pay, call, approve, or hire this service right now?

## MVP Tools

### `check_agent_action`

Broad preflight check for an intended agent action.

Inputs include buyer agent, wallet, action type, ASP ID, amount, currency, chain ID, endpoint URL, payload summary, raw payment request, and policy ID.

Output includes:

- `decision`
- `risk_score`
- `confidence`
- `summary`
- `reasons`
- `recommended_actions`
- `evidence_hash`
- `audit_id`

### `check_asp_risk`

Checks a target ASP before a call or payment.

Signals:

- listing age
- completed orders
- reviews
- disputes
- endpoint reliability
- price anomaly
- category and policy fit

### `check_payment_request`

Checks an x402 or OKX Agent Payments Protocol-style payment request against policy, known service profile, and price sanity rules.

### `check_contract_permission`

MVP stub and V1 target for contract approvals and signature risk. Detects unlimited approvals, unknown spenders, suspicious method signatures, and risky contract interactions.

## Architecture

```text
Buyer Agent
  -> AgentShield MCP Server
  -> API Gateway
  -> Policy Engine
  -> Risk Scoring Engine
  -> Endpoint Reliability Probe
  -> Payment Sanity Engine
  -> Metadata / PII Scanner
  -> Decision Composer
  -> Audit Log
```

## Decision Model

Initial risk score:

| Signal | Weight |
|---|---:|
| ASP reputation/history | 20% |
| Endpoint reliability | 15% |
| Payment risk | 15% |
| Contract/wallet risk | 20% |
| Metadata/privacy risk | 10% |
| Category/policy fit | 10% |
| Behavioral anomaly | 10% |

Thresholds:

| Score | Decision |
|---:|---|
| 0-29 | GO |
| 30-69 | CAUTION |
| 70-100 | NO-GO |

## Hackathon Demo

1. Buyer agent tries to call an unknown expensive ASP.
2. AgentShield returns `CAUTION` due to low history and price anomaly.
3. Buyer agent tries a risky unlimited approval.
4. AgentShield returns `NO-GO`.
5. Buyer selects a safer ASP.
6. AgentShield returns `GO`.
7. Payment proceeds and the check appears in the dashboard.

## Repository Contents

- `spec.md` - full product and technical specification
- `README.md` - project overview and hackathon framing

## Contributor

- eosadolor382@gmail.com

## Status

Hackathon planning repository. Implementation scaffold will add the MCP server, API service, tests, and dashboard.

