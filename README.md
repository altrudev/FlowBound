# FlowBound

FlowBound is a governed multi-agent system for consequential workflows. The hackathon demo focuses on a frontline building inspector whose agent fleet can interpret field evidence, propose remediation actions, and continue long-running follow-up without silently exceeding its authority.

## Competition track

Google All Things Agentic Hackathon — Fortified Enterprise Fleet.

## Core idea

Agents may reason freely, but consequential state transitions must remain inside an explicit authority envelope.

`current state -> evidence -> actor authority -> proposed action -> permitted effect -> execution -> successor validation`

The first executable component is the deterministic **FlowBound Gate**. Google ADK agents can propose structured actions; the gate independently returns one of:

- `ALLOW`
- `REJECT`
- `ESCALATE`
- `QUARANTINE`

## Repository status

Active competition build. The repository currently includes:

- deterministic FlowBound Gate
- Google ADK / Gemini agent definition
- Cloud Firestore transition-decision persistence adapter
- Cloud Pub/Sub workflow event publisher
- an execution path that evaluates a transition, persists its decision, and emits an asynchronous event
- reproducible unit tests for the gate and Google Cloud adapters

Cloud deployment, multimodal field evidence processing, the complete agent fleet, successor-state verification, Model Armor integration, and the judge-facing UI are being added during the hackathon period.

## Reproducible testing

### Prerequisites

- Python 3.11+
- Git

### 1. Clone

```bash
git clone https://github.com/altrudev/FlowBound.git
cd FlowBound
```

### 2. Create an isolated environment

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install the project and test dependencies

```bash
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### 4. Run the deterministic test suite

```bash
pytest -q
```

The tests do not require Google Cloud credentials. They verify authority-envelope behavior plus the Firestore/Pub/Sub integration boundaries with deterministic fake clients.

## Run the ADK agent locally

FlowBound uses Google's Agent Development Kit (`google-adk>=1.29.0`). To exercise the Gemini-backed agent, configure Application Default Credentials and a Google Cloud project:

```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
export GOOGLE_CLOUD_LOCATION="us-central1"
export GOOGLE_GENAI_USE_VERTEXAI="TRUE"
```

Then launch ADK's local developer UI:

```bash
adk web
```

Open the local URL printed by ADK and select `flowbound_agent`.

> The deterministic `pytest` suite is the reproducible baseline and remains independent of model output or cloud availability.

## Google Cloud integration

### Firestore

`flowbound/cloud_store.py` persists each gate decision beneath:

`cases/{case_id}/transitions/{transition_id}`

The stored record includes the structured transition proposal, final gate decision, and reason.

### Pub/Sub

`flowbound/events.py` publishes JSON workflow events to a configured Pub/Sub topic. `flowbound/workflow.py` currently emits `flowbound.transition.decided` after each evaluated transition.

For a live Google Cloud run, enable Firestore and Pub/Sub in the project, create a Pub/Sub topic (for example `flowbound-events`), and authenticate with Application Default Credentials or the workload identity used by the deployed runtime.

## Architecture

- **Google ADK / Gemini** — agent reasoning and structured action proposals
- **FlowBound Gate** — deterministic transition authorization
- **Cloud Firestore** — integrated durable transition/case state adapter
- **Cloud Pub/Sub** — integrated asynchronous workflow event adapter
- **Vertex AI / Google Cloud** — Gemini execution environment
- **Cloud Run / Agent Runtime** — planned deployment target
- **Model Armor** — planned untrusted-input protection layer

Only components actually integrated by submission time will be claimed in the final Devpost submission.

## License

Copyright © 2026 Altru.dev. All rights reserved unless a license is added later.
