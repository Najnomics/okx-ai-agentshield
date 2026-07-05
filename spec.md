# AgentShield Specification

## 1. Summary

AgentShield is the preflight safety layer for agent-to-agent commerce on OKX.AI. It evaluates whether an autonomous agent should trust, pay, call, approve, or hire an Agent Service Provider before taking action.

The product returns a decision of `GO`, `CAUTION`, or `NO-GO`, with a numerical risk score, evidence, and recommended next actions.

## 2. Goals

- Prevent unsafe autonomous spend.
- Reduce payment, approval, and service-selection risk.
- Give buyer agents machine-readable policy decisions.
- Give human users plain-language explanations.
- Produce audit records that can support dispute resolution, reviews, and revenue reporting.

## 3. Non-Goals

- AgentShield is not a guarantee that a transaction or service is safe.
- AgentShield is not only a wallet scanner.
- AgentShield is not tax, investment, or legal advice.
- MVP does not require full chain simulation if RPC/indexer integrations are unavailable.

## 4. Users

| User | Need |
|---|---|
| Buyer agent | Decide whether to call/pay an ASP. |
| Agent wallet | Enforce spend and approval policy. |
| ASP builder | Earn trust with reliability and risk evidence. |
| Team/DAO | Govern autonomous spending across many agents. |

## 5. Service Modes

| Capability | Mode |
|---|---|
| `check_agent_action` | A2MCP |
| `check_asp_risk` | A2MCP |
| `check_payment_request` | A2MCP |
| `check_contract_permission` | A2MCP |
| custom team policy setup | A2A |
| incident review | A2A |

## 6. Public API

### 6.1 `check_agent_action`

```json
{
  "buyer_agent_id": "agent_123",
  "wallet_address": "0xabc...",
  "action_type": "pay_and_call_asp",
  "target_asp_id": "asp_456",
  "amount": "0.05",
  "currency": "USDT",
  "chain_id": 196,
  "endpoint_url": "https://example.com/mcp",
  "payload_summary": "Get token research report",
  "raw_payment_request": {},
  "user_policy_id": "policy_default"
}
```

### 6.2 Response

```json
{
  "decision": "CAUTION",
  "risk_score": 58,
  "confidence": 0.82,
  "summary": "Payment is allowed, but the ASP is new and the price is above category median.",
  "reasons": [
    {
      "code": "NEW_ASP_LOW_HISTORY",
      "severity": "medium",
      "message": "ASP has fewer than 5 completed orders."
    },
    {
      "code": "PRICE_ANOMALY",
      "severity": "medium",
      "message": "Quoted price is 3.8x higher than similar services."
    }
  ],
  "recommended_actions": [
    "Use escrow instead of instant payment.",
    "Limit spend to 2 USDT for first call.",
    "Request WorkProof verification after delivery."
  ],
  "evidence_hash": "0x...",
  "audit_id": "ash_..."
}
```

## 7. Core Components

### 7.1 API Gateway

- Validate tool inputs.
- Authenticate dashboard users.
- Rate-limit public endpoints.
- Attach session and payment metadata.
- Route checks to engines.

### 7.2 Policy Engine

Supports policy rules such as:

```yaml
max_single_payment_usd: 5
max_daily_spend_usd: 50
allowed_service_categories:
  - research
  - developer-tools
blocked_categories:
  - gambling
  - adult
  - exploitative-finance
require_human_approval_above_usd: 10
allow_unreviewed_asps: false
allow_unlimited_contract_approvals: false
```

### 7.3 Risk Scoring Engine

Combines reputation, endpoint reliability, payment risk, contract risk, privacy risk, policy fit, and behavioral anomaly into one score.

### 7.4 Endpoint Reliability Probe

- Health check.
- Latency sample.
- Schema consistency.
- Error rate.
- TLS/HTTPS check.

### 7.5 Metadata and PII Scanner

Detects:

- API keys.
- private keys.
- seed phrases.
- access tokens.
- personal data.
- prompt-injection attempts.

### 7.6 Quote Sanity Engine

Compares requested payment against:

- service history.
- category median.
- user policy.
- similar ASPs.
- task complexity.

### 7.7 Decision Composer

Produces a final decision, reasons, recommended actions, confidence, and audit proof.

## 8. Data Model

```sql
CREATE TABLE agents (
  id UUID PRIMARY KEY,
  okx_agent_id TEXT,
  wallet_address TEXT,
  display_name TEXT,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);

CREATE TABLE policies (
  id UUID PRIMARY KEY,
  owner_agent_id UUID REFERENCES agents(id),
  policy_json JSONB NOT NULL,
  version INT NOT NULL,
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMP
);

CREATE TABLE risk_checks (
  id UUID PRIMARY KEY,
  buyer_agent_id UUID,
  target_asp_id TEXT,
  action_type TEXT,
  input_hash TEXT NOT NULL,
  decision TEXT NOT NULL,
  risk_score INT NOT NULL,
  confidence NUMERIC,
  reasons JSONB,
  evidence JSONB,
  created_at TIMESTAMP
);

CREATE TABLE asp_risk_profiles (
  asp_id TEXT PRIMARY KEY,
  reputation_score INT,
  reliability_score INT,
  dispute_rate NUMERIC,
  avg_latency_ms INT,
  completed_orders INT,
  last_checked_at TIMESTAMP,
  profile_json JSONB
);
```

## 9. MVP Scope

- A2MCP server with three working tools.
- Basic policy engine.
- Mock marketplace/reputation data.
- Endpoint probe.
- Payment amount sanity check.
- Decision report.
- Minimal dashboard.
- Demo scenarios for GO, CAUTION, and NO-GO.

## 10. V1 Scope

- Contract simulation.
- Wallet/entity risk API.
- Team policies.
- Reliability badge.
- WorkProof and Agent CFO integration.
- Analytics for blocked spend and avoided risk.

## 11. Security Requirements

- Never log private keys, seed phrases, access tokens, or full sensitive payloads.
- Hash inputs and evidence when practical.
- Rate-limit public endpoints.
- Redact sensitive metadata before model calls.
- Store prompt/tool/model versions for audit.

## 12. Hackathon Milestones

| Day | Target |
|---|---|
| 1 | MCP schemas and sample policies. |
| 2 | Risk engine and mock reputation data. |
| 3 | Endpoint probe and price sanity logic. |
| 4 | Dashboard history view. |
| 5 | Demo fixtures and seeded scenarios. |
| 6 | OKX.AI listing copy and X walkthrough. |
| 7 | Polish, deploy, submit. |

