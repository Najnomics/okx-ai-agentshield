# AgentShield Demo Script

## 90-Second Walkthrough

1. Open the deployed AgentShield API docs at `/docs`.
2. Call `/tools/check_agent_action` with the `unknown_expensive_asp` demo payload.
3. Show the `CAUTION` result, price anomaly reason, and escrow recommendation.
4. Call `/tools/check_contract_permission` with an unlimited approval payload.
5. Show the `NO-GO` result and safer limited-allowance recommendation.
6. Call `/tools/check_asp_risk` with a trusted ASP payload.
7. Show the `GO` result.
8. Open `/history` to prove the decisions are logged with audit IDs and evidence hashes.

## X Post Draft

Built AgentShield for #OKXAI: a preflight safety layer for agent commerce on X Layer. Buyer agents can check ASP risk, payment requests, and contract permissions before they pay or approve. Demo: GO / CAUTION / NO-GO decisions with audit proof.

