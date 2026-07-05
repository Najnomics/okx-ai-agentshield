import hashlib
import json
import re
from typing import Any
from uuid import uuid4

from .schemas import (
    AgentActionRequest,
    AspRiskRequest,
    ContractPermissionRequest,
    DecisionResponse,
    PaymentCheckRequest,
    Reason,
)


SECRET_PATTERNS = [
    (re.compile(r"0x[a-fA-F0-9]{64}"), "PRIVATE_KEY_LIKE_VALUE"),
    (re.compile(r"(?i)(api[_-]?key|access[_-]?token|secret)\s*[:=]\s*[\w\-]{12,}"), "SECRET_IN_PAYLOAD"),
    (re.compile(r"(?i)(seed phrase|mnemonic)"), "SEED_PHRASE_REFERENCE"),
    (re.compile(r"(?i)(ignore previous instructions|system prompt|developer message)"), "PROMPT_INJECTION_SIGNAL"),
]


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str).encode()
    return "0x" + hashlib.sha256(encoded).hexdigest()


def clamp_score(score: int) -> int:
    return max(0, min(100, score))


def decision_for(score: int) -> str:
    if score >= 70:
        return "NO-GO"
    if score >= 30:
        return "CAUTION"
    return "GO"


def detect_sensitive_text(text: str) -> list[Reason]:
    reasons: list[Reason] = []
    for pattern, code in SECRET_PATTERNS:
        if pattern.search(text):
            reasons.append(
                Reason(
                    code=code,
                    severity="high",
                    message="Payload appears to contain sensitive or adversarial metadata and should be redacted.",
                )
            )
    return reasons


def compose(tool: str, raw_input: dict[str, Any], score: int, confidence: float, reasons: list[Reason], actions: list[str]) -> dict[str, Any]:
    final_score = clamp_score(score)
    decision = decision_for(final_score)
    if not reasons:
        reasons = [Reason(code="LOW_RISK_PROFILE", severity="low", message="No major policy, price, reputation, or metadata risks detected.")]
    if not actions:
        actions = ["Proceed while keeping normal audit logging enabled."]
    summary = {
        "GO": "Risk is within policy and the action can proceed.",
        "CAUTION": "Risk is elevated; proceed only with limits, escrow, or extra verification.",
        "NO-GO": "Risk is too high for autonomous execution under the current policy.",
    }[decision]
    record = {
        "tool": tool,
        "decision": decision,
        "risk_score": final_score,
        "confidence": round(confidence, 2),
        "summary": summary,
        "reasons": [reason.model_dump() for reason in reasons],
        "recommended_actions": actions,
        "input_hash": stable_hash(raw_input),
        "evidence_hash": stable_hash({"score": final_score, "reasons": [reason.model_dump() for reason in reasons]}),
        "audit_id": f"ash_{uuid4().hex[:12]}",
    }
    return record


def check_agent_action(payload: AgentActionRequest) -> dict[str, Any]:
    score = 5
    confidence = 0.78
    reasons: list[Reason] = []
    actions: list[str] = []
    policy = payload.policy

    if payload.category in policy.blocked_categories:
        score += 80
        reasons.append(Reason(code="BLOCKED_CATEGORY", severity="critical", message=f"Category '{payload.category}' is blocked by policy."))
        actions.append("Do not call this ASP from the autonomous agent.")
    if payload.category not in policy.allowed_service_categories:
        score += 15
        reasons.append(Reason(code="CATEGORY_NOT_ALLOWLISTED", severity="medium", message=f"Category '{payload.category}' is not explicitly allowed."))
    if payload.amount > policy.max_single_payment_usd:
        score += 30
        reasons.append(Reason(code="MAX_SINGLE_PAYMENT_EXCEEDED", severity="high", message="Requested amount exceeds the policy max single payment."))
        actions.append("Require human approval or lower the payment amount.")
    if payload.amount > policy.require_human_approval_above_usd:
        score += 20
        reasons.append(Reason(code="HUMAN_APPROVAL_REQUIRED", severity="medium", message="Amount is above the configured human approval threshold."))
        actions.append("Route this payment for human approval.")
    if payload.asp_completed_orders < 5 and not policy.allow_unreviewed_asps:
        score += 18
        reasons.append(Reason(code="NEW_ASP_LOW_HISTORY", severity="medium", message="ASP has fewer than 5 completed orders."))
        actions.append("Use escrow or a low first-call limit.")
    if payload.similar_service_median_usd and payload.amount > payload.similar_service_median_usd * 3:
        score += 20
        reasons.append(Reason(code="PRICE_ANOMALY", severity="medium", message="Quoted price is more than 3x the category median."))
        actions.append("Ask for a lower quote or compare similar ASPs.")
    if payload.endpoint_url and payload.endpoint_url.scheme != "https":
        score += 20
        reasons.append(Reason(code="NON_HTTPS_ENDPOINT", severity="high", message="Endpoint is not HTTPS."))
    text = f"{payload.payload_summary} {json.dumps(payload.raw_payment_request, default=str)}"
    sensitive = detect_sensitive_text(text)
    if sensitive:
        score += 20 * len(sensitive)
        reasons.extend(sensitive)
        actions.append("Redact the payload before sending it to the ASP.")

    return compose("check_agent_action", payload.model_dump(mode="json"), score, confidence, reasons, actions)


def check_asp_risk(payload: AspRiskRequest) -> dict[str, Any]:
    score = 8
    confidence = 0.82
    reasons: list[Reason] = []
    actions: list[str] = []

    if payload.category in {"gambling", "adult", "exploitative-finance"}:
        score += 80
        reasons.append(Reason(code="HIGH_RISK_CATEGORY", severity="critical", message="Service category is blocked by the default policy."))
    if payload.completed_orders < 5:
        score += 20
        reasons.append(Reason(code="LOW_ORDER_HISTORY", severity="medium", message="ASP has limited completed-order history."))
    if payload.rating and payload.rating < 3.5:
        score += 18
        reasons.append(Reason(code="LOW_RATING", severity="medium", message="ASP rating is below 3.5."))
    if payload.dispute_rate > 0.1:
        score += 25
        reasons.append(Reason(code="HIGH_DISPUTE_RATE", severity="high", message="Dispute rate is above 10%."))
    if payload.median_category_price_usd and payload.requested_price > payload.median_category_price_usd * 3:
        score += 20
        reasons.append(Reason(code="PRICE_ANOMALY", severity="medium", message="Requested price is more than 3x the median category price."))
        actions.append("Use a capped first call or request a quote breakdown.")
    if payload.endpoint_url and payload.endpoint_url.scheme != "https":
        score += 20
        reasons.append(Reason(code="NON_HTTPS_ENDPOINT", severity="high", message="ASP endpoint is not HTTPS."))

    return compose("check_asp_risk", payload.model_dump(mode="json"), score, confidence, reasons, actions)


def check_payment_request(payload: PaymentCheckRequest) -> dict[str, Any]:
    request = payload.payment_request
    policy = request.policy
    score = 5
    confidence = 0.8
    reasons: list[Reason] = []
    actions: list[str] = []

    if request.amount > policy.max_single_payment_usd:
        score += 35
        reasons.append(Reason(code="PAYMENT_LIMIT_EXCEEDED", severity="high", message="Payment request exceeds policy max single payment."))
        actions.append("Reject or require human approval.")
    if request.amount > policy.require_human_approval_above_usd:
        score += 20
        reasons.append(Reason(code="HUMAN_APPROVAL_REQUIRED", severity="medium", message="Payment amount requires human approval."))
    if request.category in policy.blocked_categories:
        score += 80
        reasons.append(Reason(code="BLOCKED_PAYMENT_CATEGORY", severity="critical", message="Payment category is blocked."))
    sensitive = detect_sensitive_text(request.memo)
    if sensitive:
        score += 20 * len(sensitive)
        reasons.extend(sensitive)
        actions.append("Replace the memo with non-sensitive metadata.")

    return compose("check_payment_request", payload.model_dump(mode="json"), score, confidence, reasons, actions)


def check_contract_permission(payload: ContractPermissionRequest) -> dict[str, Any]:
    score = 12
    confidence = 0.74
    reasons: list[Reason] = []
    actions: list[str] = []
    calldata = payload.calldata.lower()
    approval = (payload.approval_amount or "").lower()

    unlimited_markers = ["ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff", "unlimited", "max_uint"]
    if any(marker in calldata or marker in approval for marker in unlimited_markers):
        if not payload.policy.allow_unlimited_contract_approvals:
            score += 60
            reasons.append(Reason(code="UNLIMITED_APPROVAL", severity="critical", message="Permission appears to grant unlimited allowance."))
            actions.append("Use a limited allowance matching the exact payment amount.")
    if payload.spender_reputation == "unknown":
        score += 20
        reasons.append(Reason(code="UNKNOWN_SPENDER", severity="medium", message="Spender reputation is unknown."))
    if payload.spender_reputation == "risky":
        score += 55
        reasons.append(Reason(code="RISKY_SPENDER", severity="critical", message="Spender is marked risky."))
    if payload.chain_id != 196:
        score += 8
        reasons.append(Reason(code="NON_X_LAYER_CHAIN", severity="low", message="Interaction is not on X Layer chain ID 196."))

    return compose("check_contract_permission", payload.model_dump(mode="json"), score, confidence, reasons, actions)


def validate_response(record: dict[str, Any]) -> DecisionResponse:
    return DecisionResponse.model_validate(record)

