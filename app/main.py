from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "telemetry_sample.csv"
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
RISK_POLICY_VERSION = "ssd-risk-policy-v2"

app = FastAPI(title="SSD Predictive Maintenance Platform", version="0.1.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


def load_devices() -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    with DATA_FILE.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            devices.append(
                {
                    "device_id": row["device_id"],
                    "firmware_version": row["firmware_version"],
                    "power_on_hours": int(row["power_on_hours"]),
                    "nand_erase_cycles": int(row["nand_erase_cycles"]),
                    "reallocated_block_count": int(row["reallocated_block_count"]),
                    "ecc_correction_rate": float(row["ecc_correction_rate"]),
                    "average_write_latency_ms": float(row["average_write_latency_ms"]),
                    "timeout_count": int(row["timeout_count"]),
                    "controller_reset_count": int(row["controller_reset_count"]),
                    "temperature_c": float(row["temperature_c"]),
                    "probable_subsystem": row["probable_subsystem"],
                }
            )
    return devices


DEVICES = load_devices()


def compute_risk(device: dict[str, Any]) -> dict[str, Any]:
    score = 0.08
    signals: list[str] = []
    risk_breakdown: list[dict[str, Any]] = []
    recommended_actions: list[str] = []

    def add_signal(signal: str, weight: float, metric: str, observed: Any, threshold: str) -> None:
        nonlocal score
        score += weight
        signals.append(signal)
        risk_breakdown.append(
            {
                "signal": signal,
                "weight": weight,
                "metric": metric,
                "observed": observed,
                "threshold": threshold,
            }
        )

    if device["ecc_correction_rate"] >= 0.75:
        add_signal(
            "ECC correction rate is elevated",
            0.26,
            "ecc_correction_rate",
            device["ecc_correction_rate"],
            ">= 0.75",
        )
        recommended_actions.append("Run NAND read-retry and ECC trend review")
    elif device["ecc_correction_rate"] >= 0.55:
        add_signal(
            "ECC correction rate is trending higher than normal",
            0.14,
            "ecc_correction_rate",
            device["ecc_correction_rate"],
            ">= 0.55",
        )
        recommended_actions.append("Compare ECC behavior with same firmware cohort")

    if device["timeout_count"] >= 6:
        add_signal(
            "Timeout events are above the healthy baseline",
            0.18,
            "timeout_count",
            device["timeout_count"],
            ">= 6",
        )
        recommended_actions.append("Review host timeout logs and queue reset sequence")
    elif device["timeout_count"] >= 3:
        add_signal(
            "Timeout events are appearing intermittently",
            0.10,
            "timeout_count",
            device["timeout_count"],
            ">= 3",
        )

    if device["temperature_c"] >= 66:
        add_signal(
            "Temperature is above the preferred operating range",
            0.16,
            "temperature_c",
            device["temperature_c"],
            ">= 66 C",
        )
        recommended_actions.append("Check thermal path, airflow, and workload heat profile")
    elif device["temperature_c"] >= 60:
        add_signal(
            "Temperature trend should be watched",
            0.08,
            "temperature_c",
            device["temperature_c"],
            ">= 60 C",
        )

    if device["average_write_latency_ms"] >= 5.5:
        add_signal(
            "Write latency is materially higher than expected",
            0.12,
            "average_write_latency_ms",
            device["average_write_latency_ms"],
            ">= 5.5 ms",
        )
        recommended_actions.append("Inspect FTL garbage-collection pressure and free-block pool")

    if device["controller_reset_count"] >= 3:
        add_signal(
            "Controller resets suggest device instability",
            0.10,
            "controller_reset_count",
            device["controller_reset_count"],
            ">= 3",
        )
        recommended_actions.append("Correlate controller resets with temperature and power events")

    if device["reallocated_block_count"] >= 20:
        add_signal(
            "Reallocated blocks indicate wear or degradation",
            0.14,
            "reallocated_block_count",
            device["reallocated_block_count"],
            ">= 20",
        )
        recommended_actions.append("Review bad-block growth and block retirement policy")

    if device["nand_erase_cycles"] >= 2600:
        add_signal(
            "Erase-cycle count indicates a heavily used NAND profile",
            0.10,
            "nand_erase_cycles",
            device["nand_erase_cycles"],
            ">= 2600",
        )
        recommended_actions.append("Check wear-leveling distribution and hot-block concentration")

    risk_score = round(min(score, 0.98), 2)
    if risk_score >= 0.75:
        risk_level = "high"
        priority = "P1"
        sla_hours = 4
    elif risk_score >= 0.45:
        risk_level = "medium"
        priority = "P2"
        sla_hours = 24
    else:
        risk_level = "low"
        priority = "P3"
        sla_hours = 72

    owner_team = {
        "Host": "Firmware Host Interface",
        "FTL": "Firmware FTL",
        "NAND": "NAND Reliability",
        "Hardware": "Hardware Validation",
    }.get(device["probable_subsystem"], "Reliability Triage")

    if len(risk_breakdown) >= 4:
        confidence = {"level": "high", "reason": "Multiple independent telemetry signals agree"}
    elif len(risk_breakdown) >= 2:
        confidence = {"level": "medium", "reason": "Several signals point to the same risk area"}
    else:
        confidence = {"level": "low", "reason": "Limited evidence; continue monitoring"}

    return {
        "alert_id": f"ALERT-{device['device_id'].upper()}",
        "policy_version": RISK_POLICY_VERSION,
        "health_score": round(max(0.0, 1.0 - risk_score), 2),
        "risk_score": risk_score,
        "risk_level": risk_level,
        "priority": priority,
        "sla_hours": sla_hours,
        "owner_team": owner_team,
        "probable_subsystem": device["probable_subsystem"],
        "top_signals": signals or ["No critical signals detected"],
        "risk_breakdown": risk_breakdown
        or [
            {
                "signal": "Baseline monitoring only",
                "weight": 0.08,
                "metric": "baseline",
                "observed": "normal",
                "threshold": "no elevated signal",
            }
        ],
        "confidence": confidence,
        "recommended_actions": recommended_actions
        or ["Keep unit in normal monitoring rotation and compare against fleet baseline"],
    }


def build_fallback_explanation(device: dict[str, Any], prediction: dict[str, Any]) -> str:
    signal_summary = "; ".join(prediction["top_signals"])
    return (
        f"Device {device['device_id']} is rated {prediction['risk_level']} risk with a score of "
        f"{prediction['risk_score']}. The strongest signals are: {signal_summary}. "
        f"The most likely investigation area is {prediction['probable_subsystem']}. "
        f"Owner team: {prediction['owner_team']}. "
        f"Action window: {prediction['sla_hours']} hours. "
        f"Recommended next actions: {'; '.join(prediction['recommended_actions'][:3])}."
    )


def get_openai_client() -> Any | None:
    if OpenAI is None or not os.getenv("OPENAI_API_KEY"):
        return None
    return OpenAI()


def generate_explanation(device: dict[str, Any], prediction: dict[str, Any]) -> str:
    client = get_openai_client()
    if client is None:
        return build_fallback_explanation(device, prediction)

    prompt = {
        "device": device,
        "prediction": prediction,
        "task": (
            "Write a concise engineering summary for an SSD predictive maintenance dashboard. "
            "Explain the likely issue area, highlight the strongest telemetry signals, and "
            "recommend the next validation steps. Do not invent metrics not present in the input."
        ),
    }
    response = client.responses.create(
        model=DEFAULT_MODEL,
        input=json.dumps(prompt),
    )
    return response.output_text.strip()


def fleet_summary() -> dict[str, Any]:
    enriched = [{**device, **compute_risk(device)} for device in DEVICES]
    risk_counts = {"high": 0, "medium": 0, "low": 0}
    subsystem_counts: dict[str, int] = {}
    for item in enriched:
        risk_counts[item["risk_level"]] += 1
        subsystem_counts[item["probable_subsystem"]] = subsystem_counts.get(item["probable_subsystem"], 0) + 1
    sorted_items = sorted(enriched, key=lambda item: item["risk_score"], reverse=True)
    return {
        "total_devices": len(enriched),
        "risk_counts": risk_counts,
        "subsystem_counts": subsystem_counts,
        "average_risk_score": round(sum(item["risk_score"] for item in enriched) / len(enriched), 2),
        "highest_risk_device": sorted_items[0]["device_id"],
        "p1_alerts": sum(1 for item in enriched if item["priority"] == "P1"),
    }


def alert_queue() -> list[dict[str, Any]]:
    enriched = [{**device, **compute_risk(device)} for device in DEVICES]
    return sorted(
        enriched,
        key=lambda item: (item["priority"], -item["risk_score"]),
    )


def build_work_order(item: dict[str, Any]) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat()
    primary_metric = item["risk_breakdown"][0]
    return {
        "work_order_id": f"WO-{item['device_id'].upper()}",
        "alert_id": item["alert_id"],
        "generated_at_utc": generated_at,
        "device_id": item["device_id"],
        "priority": item["priority"],
        "risk_level": item["risk_level"],
        "risk_score": item["risk_score"],
        "owner_team": item["owner_team"],
        "sla_hours": item["sla_hours"],
        "primary_hypothesis": f"{item['probable_subsystem']} issue driven by {primary_metric['metric']}",
        "evidence_bundle": {
            "device_id": item["device_id"],
            "firmware_version": item["firmware_version"],
            "policy_version": item["policy_version"],
            "risk_breakdown": item["risk_breakdown"],
            "confidence": item["confidence"],
        },
        "runbook_steps": [
            "Freeze the affected unit cohort and preserve logs before power cycling.",
            "Compare this device against the same firmware and NAND-lot baseline.",
            *item["recommended_actions"],
            "Record disposition: monitor, firmware investigation, RMA analysis, or release hold.",
        ],
        "closure_criteria": [
            "Risk-driving metric is explained or reproduced.",
            "Owner team confirms next action and expected mitigation.",
            "Follow-up telemetry window is defined.",
        ],
    }


def work_order_queue() -> list[dict[str, Any]]:
    return [build_work_order(item) for item in alert_queue()]


def generate_trend_points(device: dict[str, Any]) -> list[dict[str, Any]]:
    base_risk = compute_risk(device)["risk_score"]
    points = []
    for day in range(1, 8):
        drift = (day - 4) * 0.025
        points.append(
            {
                "day": f"D-{7 - day}",
                "risk_score": round(min(0.98, max(0.05, base_risk + drift)), 2),
                "temperature_c": round(device["temperature_c"] + (day - 4) * 0.8, 1),
                "ecc_correction_rate": round(max(0.01, device["ecc_correction_rate"] + (day - 4) * 0.025), 2),
            }
        )
    return points


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {"model_name": DEFAULT_MODEL, "device_count": len(DEVICES)},
    )


@app.get("/api/devices")
async def list_devices() -> JSONResponse:
    items = []
    for device in DEVICES:
        prediction = compute_risk(device)
        items.append({**device, **prediction})
    return JSONResponse({"devices": items, "model_name": DEFAULT_MODEL})


@app.get("/api/fleet-summary")
async def get_fleet_summary() -> JSONResponse:
    return JSONResponse({"summary": fleet_summary(), "model_name": DEFAULT_MODEL})


@app.get("/api/alerts")
async def get_alerts() -> JSONResponse:
    return JSONResponse({"alerts": alert_queue()})


@app.get("/api/work-orders")
async def get_work_orders() -> JSONResponse:
    return JSONResponse(
        {
            "policy_version": RISK_POLICY_VERSION,
            "work_orders": work_order_queue(),
            "operating_model": "prioritized maintenance queue with owner, SLA, evidence, and closure criteria",
        }
    )


@app.get("/api/devices/{device_id}")
async def get_device(device_id: str) -> JSONResponse:
    device = next((item for item in DEVICES if item["device_id"] == device_id), None)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    prediction = compute_risk(device)
    explanation = generate_explanation(device, prediction)
    return JSONResponse(
        {
            "device": device,
            "prediction": prediction,
            "trend": generate_trend_points(device),
            "explanation": explanation,
        }
    )


@app.get("/api/report")
async def fleet_report() -> JSONResponse:
    summary = fleet_summary()
    alerts = alert_queue()[:3]
    work_orders = work_order_queue()[:3]
    report = (
        f"Fleet risk average is {summary['average_risk_score']} across {summary['total_devices']} devices. "
        f"There are {summary['p1_alerts']} P1 alerts. Highest-risk device is "
        f"{summary['highest_risk_device']}. Top review items: "
        + "; ".join(f"{item['device_id']} ({item['priority']}, {item['probable_subsystem']})" for item in alerts)
    )
    return JSONResponse({"summary": summary, "top_alerts": alerts, "top_work_orders": work_orders, "report": report})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "policy_version": RISK_POLICY_VERSION}
