# FlowBound

FlowBound is a governed multi-agent system for consequential workflows. The Google All Things Agentic Hackathon demo focuses on a frontline building inspector whose agent fleet can interpret field evidence, propose remediation actions, and continue long-running follow-up without silently exceeding its authority.

**Track:** Fortified Enterprise Fleet  
**Repository:** https://github.com/altrudev/FlowBound  
**Created by:** Valentyn Rukhaylo · Altru.dev

## Core invariant

Agents may reason freely, but consequential state transitions must remain inside an explicit authority envelope.

`originating need -> authority/policy -> exact predecessor -> proposed effect -> gate -> execution -> successor verification -> accept or recovery block`

The model proposes an effect. It does **not** supply its own authority or successor state. Server-side FlowBound policy determines the required authority and expected successor.

## Current vertical slice

The repository now contains a runnable end-to-end application path:

1. a case is created with revisioned state (`OPEN@0`)
2. a Google ADK fleet reasons over the inspector observation
3. the final agent emits a structured effect proposal
4. FlowBound re-reads the exact predecessor state after model reasoning
5. the deterministic Gate returns `ALLOW`, `REJECT`, `ESCALATE`, or `QUARANTINE`
6. an allowed effect executes through compare-and-set state mutation
7. Firestore persists decision/execution/verification evidence
8. Pub/Sub emits transition events
9. the verifier independently re-reads observed state rather than trusting the executor receipt
10. a conformant successor is explicitly accepted; a mismatch blocks the case for recovery

### Google ADK fleet

`flowbound_agent/agent.py` defines three Gemini 3.5 Flash specialists:

- **Intake Agent** — separates field observations from assumptions
- **Evidence Agent** — challenges evidence and suspicious instruction-like content
- **Action Agent** — emits one structured policy-named effect and never claims authorization

The agents run sequentially through Google ADK. `flowbound/adk_client.py` bridges the fleet's structured final proposal into the deterministic FlowBound transition path.

### FlowBound transition boundary

`flowbound/policy.py` owns the demo state machine and authority mapping. The model can request a named effect, but policy derives its legal predecessor, required authority, successor state, and human-approval rule.

Exact state identity is revision-bound. A proposal captured at `OPEN@0` is rejected if the case becomes `OPEN@1` or any other state/revision before authorization.

Firestore execution uses transactional compare-and-set to close the race between authorization and mutation.

## Reproducible testing

### Prerequisites

- Python 3.11+
- Git

```bash
git clone https://github.com/altrudev/FlowBound.git
cd FlowBound
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest -q
```

Current deterministic suite: **22 tests**.

The suite covers:

- allowed transitions
- stale predecessor state and revision
- state change during model reasoning
- authority mismatch
- out-of-envelope and unknown effects
- quarantine of untrusted evidence
- explicit human escalation
- Firestore/Pub/Sub adapter behavior
- compare-and-set race protection
- successful execute/verify/accept lineage
- a deliberately lying executor whose success claim is rejected by successor verification

The deterministic suite requires no Google Cloud credentials. Cloud/model execution is a separate integration gate.

## Run locally without Google credentials

The local development fallback lets the full API/UI and deterministic transition path run without spending model/cloud quota:

```bash
export FLOWBOUND_BACKEND=memory
export FLOWBOUND_AGENT_MODE=demo
uvicorn flowbound.api:app --reload
```

Open `http://127.0.0.1:8000`.

`FLOWBOUND_AGENT_MODE=demo` is a development fallback only. It is **not** the hackathon proof path and must not be presented as Gemini execution.

## Run the Google ADK fleet locally

Authenticate and select Vertex AI:

```bash
gcloud auth application-default login
export GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
export GOOGLE_CLOUD_LOCATION="global"
export GOOGLE_GENAI_USE_VERTEXAI="TRUE"
export FLOWBOUND_BACKEND=memory
export FLOWBOUND_AGENT_MODE=google
uvicorn flowbound.api:app --reload
```

Gemini 3.5 Flash is the configured model for all three ADK agents.

## Google Cloud path

Integrated code paths exist for:

- **Vertex AI / Gemini 3.5 Flash** through Google ADK
- **Cloud Firestore** for durable case and transition evidence
- **Cloud Pub/Sub** for asynchronous transition events
- **Cloud Run** deployment via `Dockerfile` and `scripts/deploy-cloud-run.sh`

### Deployment prerequisites

The deployment script deliberately avoids creating/deleting Firestore automatically. Before running it:

1. select/create the Google Cloud project
2. enable billing as required by Google Cloud
3. create the default Firestore Native database
4. authenticate `gcloud`

Then:

```bash
export GOOGLE_CLOUD_PROJECT="YOUR_PROJECT_ID"
export GOOGLE_CLOUD_LOCATION="global"
./scripts/deploy-cloud-run.sh
```

The script:

- enables the required APIs
- creates the Pub/Sub topic if missing
- creates a dedicated FlowBound runtime service account if missing
- grants only `datastore.user`, `pubsub.publisher`, and `aiplatform.user`
- verifies the default Firestore database exists
- deploys the container to Cloud Run
- prints the resulting Cloud Run URL

**Important:** deployment configuration is not deployment evidence. As of this README revision, the repository is prepared for the authenticated Google Cloud integration step; the final Devpost submission should only claim the live services after they have actually been exercised and captured in runtime evidence.

## DDC review

A reproducible architecture review is committed at:

`docs/DDC-REVIEW-2026-08-26.md`

It uses the canonical DDC standing-principles registry at commit:

`376e5d75d2a6cdef557eb8acccfd24cfba238ec8`

### Current DDC disposition

**STAGE / ACCEPT FOR GOOGLE CLOUD INTEGRATION TESTING. NOT YET FINAL PRODUCTION ASSURANCE.**

The review specifically records unresolved work rather than claiming it is complete:

- evidence-trust classification still needs an independent cloud security boundary (for example Model Armor + deterministic policy)
- successor verification is independent of the executor receipt but still shares the same process/state-store failure domain
- independent recovery evidence/unblocking is not yet implemented
- Google Cloud runtime execution evidence is still required

## Architecture responsibility split

| Layer | Responsibility |
| --- | --- |
| Gemini 3.5 Flash | probabilistic interpretation/reasoning |
| Google ADK | specialist-agent orchestration |
| FlowBound policy | named effects, predecessor rules, required authority, successor state |
| FlowBound Gate | deterministic authorization decision |
| Firestore transaction | exact compare-and-set state mutation |
| Successor verifier | independently observe and compare resulting state |
| Pub/Sub | asynchronous transition/event lineage |
| Recovery block | fail closed when successor evidence does not conform |

## Next build gates

1. authenticate a Google Cloud project and run the ADK fleet against Gemini 3.5 Flash
2. create Firestore and Pub/Sub resources and exercise the real adapters
3. deploy to Cloud Run and capture the `.run` URL/log evidence
4. replace the demo evidence-trust input with Model Armor / independent classification
5. strengthen postcondition verification across a more independent failure domain
6. expand the inspector UI for the final adversarial demo
7. only then record the required public demo video

## License

Copyright © 2026 Altru.dev. All rights reserved unless a license is added later.
