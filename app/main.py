from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings, get_settings
from .schemas import AgentActionRequest, AspRiskRequest, ContractPermissionRequest, PaymentCheckRequest
from .service import check_agent_action, check_asp_risk, check_contract_permission, check_payment_request, validate_response
from .storage import AuditStore

app = FastAPI(
    title="AgentShield",
    version="0.1.0",
    description="Preflight risk, trust, and spend-control checks for OKX.AI agent commerce.",
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.cors_origins == "*" else [item.strip() for item in settings.cors_origins.split(",")],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
store = AuditStore(settings.data_dir)


def require_api_key(x_api_key: str | None = Header(default=None), config: Settings = Depends(get_settings)) -> None:
    if config.api_key and x_api_key != config.api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


def persist(record: dict) -> dict:
    store.insert(record)
    return record


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "agentshield", "mode": "A2MCP", "chain_id": 196}


@app.get("/mcp")
def mcp_manifest() -> dict:
    return {
        "name": "AgentShield",
        "version": "0.1.0",
        "service_mode": "A2MCP",
        "tools": [
            {"name": "check_agent_action", "endpoint": "/tools/check_agent_action"},
            {"name": "check_asp_risk", "endpoint": "/tools/check_asp_risk"},
            {"name": "check_payment_request", "endpoint": "/tools/check_payment_request"},
            {"name": "check_contract_permission", "endpoint": "/tools/check_contract_permission"},
        ],
    }


@app.post("/tools/check_agent_action", dependencies=[Depends(require_api_key)])
def tool_check_agent_action(payload: AgentActionRequest) -> dict:
    return validate_response(persist(check_agent_action(payload))).model_dump()


@app.post("/tools/check_asp_risk", dependencies=[Depends(require_api_key)])
def tool_check_asp_risk(payload: AspRiskRequest) -> dict:
    return validate_response(persist(check_asp_risk(payload))).model_dump()


@app.post("/tools/check_payment_request", dependencies=[Depends(require_api_key)])
def tool_check_payment_request(payload: PaymentCheckRequest) -> dict:
    return validate_response(persist(check_payment_request(payload))).model_dump()


@app.post("/tools/check_contract_permission", dependencies=[Depends(require_api_key)])
def tool_check_contract_permission(payload: ContractPermissionRequest) -> dict:
    return validate_response(persist(check_contract_permission(payload))).model_dump()


@app.get("/history", dependencies=[Depends(require_api_key)])
def history(limit: int = 50) -> dict:
    return {"items": store.list_recent(limit=limit)}


@app.get("/demo")
def demo_payloads() -> dict:
    return {
        "unknown_expensive_asp": {
            "endpoint": "/tools/check_agent_action",
            "payload": {
                "buyer_agent_id": "agent_demo",
                "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
                "action_type": "pay_and_call_asp",
                "target_asp_id": "asp_new_expensive",
                "amount": 25,
                "currency": "USDT",
                "chain_id": 196,
                "endpoint_url": "https://new-asp.example/mcp",
                "payload_summary": "Get token research report",
                "category": "research",
                "asp_completed_orders": 1,
                "similar_service_median_usd": 2,
            },
        },
        "unlimited_approval": {
            "endpoint": "/tools/check_contract_permission",
            "payload": {
                "wallet_address": "0x1234567890abcdef1234567890abcdef12345678",
                "chain_id": 196,
                "target_contract": "0x9999999999999999999999999999999999999999",
                "calldata": "0x095ea7b3ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
                "human_readable_intent": "Approve service payment",
                "spender_reputation": "unknown",
            },
        },
        "trusted_asp": {
            "endpoint": "/tools/check_asp_risk",
            "payload": {
                "asp_id": "asp_trusted_workproof",
                "service_name": "WorkProof Lead Verification",
                "endpoint_url": "https://workproof.example/mcp",
                "category": "software-utility",
                "requested_price": 0.05,
                "completed_orders": 124,
                "rating": 4.8,
                "dispute_rate": 0.01,
                "median_category_price_usd": 0.05,
            },
        },
    }

