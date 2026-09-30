# Devpost Submission Draft — FlowBound

## Tagline

Governed multi-agent execution for frontline inspection workflows, where models can propose action but cannot exceed explicit authority.

## Inspiration

AI agents are increasingly able to act, not just answer. The hard problem is no longer whether an agent can call a tool; it is whether a specific state change is authorized now, from this exact predecessor state, with evidence that can be verified afterward.

FlowBound focuses on that boundary. A frontline inspector can provide messy field evidence, an ADK agent fleet can interpret it, and the system can continue the workflow autonomously—but consequential transitions remain inside a deterministic authority envelope.

## What it does

FlowBound runs a governed inspection workflow with three specialist agents: Intake, Evidence, and Action. The agent fleet produces a structured named-effect proposal. FlowBound then re-reads the exact case state, resolves the server-side policy rule, verifies the actor authority, and either rejects, escalates, quarantines, or executes the transition.

Execution is compare-and-set against the exact state revision. After execution, FlowBound does not trust the executor receipt. It independently re-reads the successor state and accepts the transition only if the observed state and revision match the policy-derived postcondition. Any mismatch creates a recovery block.

The current v0.3 hardening also removes caller-controlled trust. Obvious instruction-like, tool-directive, or exfiltration-like evidence is quarantined before the model is invoked. Clearing a recovery block requires a separate recovery:clear authority plus explicit independent evidence.

## How we built it

- Python 3.11 and FastAPI
- Google Agent Development Kit
- Gemini 3.5 Flash through Vertex AI
- Cloud Firestore for durable case and transition evidence
- Cloud Pub/Sub for event lineage
- Cloud Run deployment path
- Deterministic FlowBound policy/gate/executor/verifier layer
- Pytest regression suite

## Challenges

The main design challenge was separating reasoning from authority. A model can be very capable and still should not decide whether its own proposed state mutation is authorized. The same separation is required after execution: an executor saying success is not proof that the authorized postcondition actually exists.

Another challenge was stale state. A proposal that was valid for OPEN@0 can become invalid while the agents are reasoning. FlowBound binds authorization to the exact revision and uses compare-and-set execution so stale proposals fail closed.

## Accomplishments

- Exact revision-bound authorization
- Policy-owned successor states
- Named capability/authority checks
- Human escalation for sensitive transitions
- Pre-model quarantine without caller self-attestation
- Receipt-independent successor verification
- Fail-closed recovery blocking
- Separate evidence-backed recovery authority
- Durable transition and recovery provenance
- 25 deterministic tests

## What we learned

Agent safety is not a prompt-writing problem. The useful boundary is architectural: need is not authority, evidence is not authority, execution is not evidence, and retry is not recovery. Once those are explicit, the model can be given meaningful freedom inside a much clearer operating envelope.

## What's next

The next proof step is authenticated Google Cloud runtime evidence: exercise the real ADK/Gemini path, Firestore, Pub/Sub, and Cloud Run deployment; capture the hosted URL and logs; and move successor observation into a more independent failure domain. The local pre-model trust boundary can also be augmented with a stronger independent cloud classifier while preserving the same provenance contract.

## Repository

https://github.com/altrudev/FlowBound

## Architecture

See docs/ARCHITECTURE.md.

## Claim discipline

Do not claim a live Google Cloud deployment until the Cloud Run / Vertex AI / Firestore / Pub/Sub path has actually been exercised and captured.