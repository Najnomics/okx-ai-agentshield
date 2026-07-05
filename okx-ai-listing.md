# OKX.AI Listing Draft: AgentShield

## Service Name

AgentShield

## Short Description

Preflight risk, trust, and spend-control checks for autonomous agents before they pay, call, approve, or hire an ASP.

## Category

Software Utility / Finance Copilot

## Service Mode

A2MCP

## Suggested Pricing

- Basic risk check: 0.03 USDT per call
- Deep policy and permission check: 0.15 USDT per call

## Tools

- `check_agent_action`
- `check_asp_risk`
- `check_payment_request`
- `check_contract_permission`

## Example Prompt

Before paying this ASP, call AgentShield and tell me whether this agent action is GO, CAUTION, or NO-GO. Include the reasons and recommended next action.

## Demo Summary

A buyer agent attempts an expensive unknown ASP call, a risky unlimited approval, and a safer low-risk ASP call. AgentShield blocks or cautions the risky flows and logs every decision.

