from fastapi.testclient import TestClient

from app.main import DEVICES, app, build_work_order, compute_risk


client = TestClient(app)


def test_risk_prediction_contains_weighted_breakdown():
    prediction = compute_risk(DEVICES[1])

    assert prediction["risk_breakdown"]
    assert all("signal" in item and "weight" in item for item in prediction["risk_breakdown"])
    assert prediction["confidence"]["level"] in {"high", "medium", "low"}
    assert prediction["policy_version"] == "ssd-risk-policy-v2"


def test_work_order_contains_sla_owner_and_evidence_bundle():
    prediction = compute_risk(DEVICES[1])
    work_order = build_work_order({**DEVICES[1], **prediction})

    assert work_order["work_order_id"].startswith("WO-")
    assert work_order["owner_team"] == prediction["owner_team"]
    assert work_order["sla_hours"] == prediction["sla_hours"]
    assert work_order["evidence_bundle"]["device_id"] == DEVICES[1]["device_id"]


def test_work_orders_endpoint_prioritizes_actionable_alerts():
    response = client.get("/api/work-orders")

    assert response.status_code == 200
    payload = response.json()

    assert payload["policy_version"] == "ssd-risk-policy-v2"
    assert payload["work_orders"]
    assert payload["work_orders"][0]["priority"] in {"P1", "P2", "P3"}
