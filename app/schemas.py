from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl


Decision = Literal["GO", "CAUTION", "NO-GO"]
Severity = Literal["low", "medium", "high", "critical"]


class Policy(BaseModel):
    max_single_payment_usd: float = 5
    max_daily_spend_usd: float = 50
    allowed_service_categories: list[str] = Field(default_factory=lambda: ["research", "developer-tools", "software-utility"])
    blocked_categories: list[str] = Field(default_factory=lambda: ["gambling", "adult", "exploitative-finance"])
    require_human_approval_above_usd: float = 10
    allow_unreviewed_asps: bool = False
    allow_unlimited_contract_approvals: bool = False


class AgentActionRequest(BaseModel):
    buyer_agent_id: str = "agent_demo"
    wallet_address: str | None = None
    action_type: str = "pay_and_call_asp"
    target_asp_id: str | None = None
    amount: float = 0
    currency: str = "USDT"
    chain_id: int = 196
    endpoint_url: HttpUrl | None = None
    payload_summary: str = ""
    raw_payment_request: dict[str, Any] = Field(default_factory=dict)
    user_policy_id: str = "policy_default"
    category: str = "research"
    asp_completed_orders: int = 0
    asp_rating: float = 0
    similar_service_median_usd: float = 0.05
    policy: Policy = Field(default_factory=Policy)


class AspRiskRequest(BaseModel):
    asp_id: str = "asp_demo"
    service_name: str = "Token Research API"
    endpoint_url: HttpUrl | None = None
    category: str = "research"
    requested_price: float = 0.05
    currency: str = "USDT"
    completed_orders: int = 0
    rating: float = 0
    dispute_rate: float = 0
    median_category_price_usd: float = 0.05


class PaymentRequestPayload(BaseModel):
    seller: str
    buyer: str | None = None
    amount: float
    currency: str = "USDT"
    memo: str = ""
    expires_at: str | None = None
    category: str = "research"
    policy: Policy = Field(default_factory=Policy)


class PaymentCheckRequest(BaseModel):
    payment_request: PaymentRequestPayload
    policy_id: str = "policy_default"


class ContractPermissionRequest(BaseModel):
    wallet_address: str
    chain_id: int = 196
    target_contract: str
    calldata: str = ""
    human_readable_intent: str = "Approve service payment"
    spender_reputation: Literal["known", "unknown", "risky"] = "unknown"
    approval_amount: str | None = None
    policy: Policy = Field(default_factory=Policy)


class Reason(BaseModel):
    code: str
    severity: Severity
    message: str


class DecisionResponse(BaseModel):
    decision: Decision
    risk_score: int
    confidence: float
    summary: str
    reasons: list[Reason]
    recommended_actions: list[str]
    evidence_hash: str
    audit_id: str


class ToolDescriptor(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]

