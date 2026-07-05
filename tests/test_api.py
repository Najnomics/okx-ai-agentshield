from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_payment_policy_caution_or_nogo() -> None:
    response = client.post(
        "/tools/check_payment_request",
        json={
            "payment_request": {
                "seller": "0xseller",
                "buyer": "0xbuyer",
                "amount": 25,
                "currency": "USDT",
                "memo": "Research report",
                "category": "research",
            },
            "policy_id": "policy_default",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] in {"CAUTION", "NO-GO"}
    assert body["risk_score"] >= 30
    assert body["audit_id"].startswith("ash_")


def test_contract_unlimited_approval_is_nogo() -> None:
    response = client.post(
        "/tools/check_contract_permission",
        json={
            "wallet_address": "0xabc",
            "chain_id": 196,
            "target_contract": "0xdef",
            "calldata": "0x095ea7b3ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff",
            "spender_reputation": "unknown",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "NO-GO"
    assert any(reason["code"] == "UNLIMITED_APPROVAL" for reason in body["reasons"])

