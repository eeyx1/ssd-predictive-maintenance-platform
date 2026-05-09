# SSD Predictive Maintenance and Failure Analysis Platform

This project is an industrial-style SSD reliability dashboard for predictive maintenance, telemetry triage, and failure-analysis support. It is part of a Maistorage-focused AI portfolio.

## Industry Problem

SSD and NAND-based devices produce many reliability signals:

- ECC correction rate
- timeout count
- controller reset count
- temperature
- write latency
- NAND erase cycles
- bad or reallocated blocks
- firmware version

Engineering teams need to know which devices require attention first, who should own the issue, and what validation action should happen next.

This project turns raw telemetry into a fleet risk view, alert queue, owner assignment, action window, and AI-assisted investigation summary.

## Who Would Use It

- Reliability engineer monitoring device health
- Firmware engineer checking suspicious telemetry
- RMA engineer triaging returned devices
- Data center storage operations team
- AI engineer building industrial decision-support tools

## Industrial Features

### 1. Fleet-Level Risk KPIs

The dashboard calculates:

- average fleet risk score
- number of high-risk devices
- number of P1 alerts
- highest-risk device

Why it helps industry:

- managers and engineers can quickly see fleet health
- high-risk devices are visible without reading every row
- it supports daily reliability standups or RMA triage meetings

### 2. Device Health and Risk Scoring

Each device receives:

- `risk_score`
- `health_score`
- `risk_level`
- `priority`
- `sla_hours`

Risk is based on telemetry such as ECC correction rate, temperature, timeouts, controller resets, reallocated blocks, write latency, and erase cycles.

Why it helps industry:

- raw telemetry becomes a decision metric
- devices can be sorted by risk
- engineers can focus on the units most likely to fail

### 3. Alert Queue

The app creates an alert queue with:

- alert ID
- device ID
- priority
- owner team
- action window

Why it helps industry:

- reliability issues become trackable work items
- teams can route issues to Host, FTL, NAND, or Hardware owners
- it mimics a real engineering operations workflow

### 4. Owner Team Assignment

Probable subsystem is mapped to an owner:

- `Host` -> Firmware Host Interface
- `FTL` -> Firmware FTL
- `NAND` -> NAND Reliability
- `Hardware` -> Hardware Validation

Why it helps industry:

- reduces handoff confusion
- helps triage meetings assign responsibility
- matches storage-controller engineering layers

### 5. Recommended Actions

The app generates action suggestions based on risk drivers.

Examples:

- high ECC -> review NAND margin and read-retry trend
- high timeout -> inspect host timeout and queue reset sequence
- high temperature -> check thermal path and workload heat profile
- high write latency -> inspect FTL garbage-collection pressure

Why it helps industry:

- output becomes useful for debugging
- junior engineers get a starting checklist
- senior engineers can quickly validate the logic

### 6. 7-Day Risk Trace

The app generates a simple risk trace for each device to show whether the unit is trending toward higher concern.

Why it helps industry:

- trend direction matters more than one snapshot
- it supports early-warning thinking
- it creates a path for future real time-series telemetry integration

### 7. Fleet Report Endpoint

The app can generate a fleet summary report with top alerts.

Why it helps industry:

- supports daily/weekly reliability reporting
- gives managers a concise view of current fleet risk
- can be extended into email, PDF, or ticket automation

## Industrial v2 Upgrade

### 1. Weighted Risk Breakdown

Each device prediction now includes `risk_breakdown`, a list of risk-driving signals with:

- signal name
- weight added to the score
- telemetry metric
- observed value
- threshold that triggered the signal

Why it helps industry:

- reliability engineers can explain why a device is high risk
- the scoring logic is easier to tune and review
- it avoids a black-box dashboard result

### 2. Confidence and Policy Versioning

Each prediction now includes:

- `policy_version`: `ssd-risk-policy-v2`
- confidence level
- confidence reason

Why it helps industry:

- teams can track which scoring policy produced an alert
- reviewers know whether multiple independent signals support the result
- it creates a cleaner path for model governance and future ML replacement

### 3. Maintenance Work Orders

The new `/api/work-orders` endpoint converts alerts into work orders with:

- work order ID
- owner team
- SLA hours
- primary hypothesis
- evidence bundle
- runbook steps
- closure criteria

Why it helps industry:

- alerts become executable engineering tasks
- owner teams know what evidence to inspect
- managers can track whether high-risk devices were handled within SLA

### 4. Industrial Delivery Readiness

The project now includes:

- automated tests for risk breakdown, work-order generation, and API behavior
- `Dockerfile` for reproducible deployment
- `.env.example` for configuration
- GitHub Actions CI to run tests on push and pull request

## Tech Stack

- Python
- FastAPI
- CSV telemetry processing
- Jinja2 templates
- HTML/CSS dashboard
- optional OpenAI Responses API

## Default Model

Default:

```text
gpt-5.4-mini
```

Why:

- numerical scoring is handled by code
- the model is used for repeated report-style explanations
- speed and cost matter for dashboard summaries

For maximum summary quality:

```bash
OPENAI_MODEL=gpt-5.4
```

The app still works without an API key using deterministic fallback reports.

## Project Structure

```text
app/
  main.py                 risk scoring, alert queue, fleet summary, report API
  templates/index.html    fleet reliability operations console
  static/styles.css       operational dashboard styling
data/
  telemetry_sample.csv    sample SSD telemetry
tests/
  test_industrial_features.py
Dockerfile                container runtime
.github/workflows/ci.yml  GitHub Actions test workflow
.env.example              environment variable template
requirements.txt          dependencies
requirements-dev.txt      test dependencies
README.md                 project guide
```

## API Endpoints

- `GET /` opens the dashboard
- `GET /api/devices` lists devices with risk scores
- `GET /api/devices/{device_id}` returns device detail, trend, actions, and explanation
- `GET /api/fleet-summary` returns fleet-level KPIs
- `GET /api/alerts` returns prioritized alert queue
- `GET /api/work-orders` returns maintenance work orders with owner, SLA, evidence, and closure criteria
- `GET /api/report` returns a fleet reliability report
- `GET /health` checks service status

## How To Run

```bash
cd "G:\Ai Project\ssd-predictive-maintenance-platform"
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

Optional:

```bash
set OPENAI_API_KEY=your_key
set OPENAI_MODEL=gpt-5.4-mini
```

## Testing

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest tests -q
```

## Docker

```bash
docker build -t ssd-predictive-maintenance .
docker run --rm -p 8000:8000 --env-file .env.example ssd-predictive-maintenance
```

## Demo Flow

1. Open the dashboard and show fleet KPIs.
2. Point out high-risk and P1 devices.
3. Click `ssd_102` or another risky unit.
4. Explain the top signals and owner team.
5. Show the recommended actions and 7-day risk trace.
6. Generate a fleet report.

## Interview Explanation

Say this:

> This project simulates an SSD reliability operations console. It converts telemetry into risk scores, alert priority, owner-team assignment, recommended actions, and engineering summaries. The goal is to help storage teams identify risky devices earlier and route investigation to the right Host, FTL, NAND, or Hardware owner.

## Resume Bullet

Developed an SSD predictive maintenance platform using Python and FastAPI to analyze telemetry, score device health risk, prioritize alerts, assign subsystem owner teams, and generate AI-assisted failure-analysis summaries.

## Production Hardening Ideas

- use real historical telemetry and failure labels
- add time-series database support
- add anomaly detection models such as Isolation Forest
- integrate with ticketing systems
- add alert acknowledgement and status tracking
- export PDF reports
- persist work orders and alert acknowledgement history
