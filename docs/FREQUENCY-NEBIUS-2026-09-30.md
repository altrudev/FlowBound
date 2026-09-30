# Frequency Review — FlowBound Nebius/NVIDIA Adaptation — 2026-09-30

## Scope

Frequency sweep of the competition adaptation for the Nebius × NVIDIA Global AI Hackathon, including track fit, provider integration, authority boundaries, provenance, adversarial-input handling, runtime evidence, licensing, repository exposure, and submission requirements.

## Disposition

**STAGE / ACCEPT FOR LIVE NEBIUS INTEGRATION TESTING. DO NOT MERGE OR SUBMIT YET.**

The adapter is structurally ready and the deterministic suite passes. Two external gates remain: a live Token Factory key/runtime proof and a submission-compatible open-source repository boundary.

## Architecture result

The competition path preserves the governing chain:

`evidence -> pre-model trust boundary -> Nemotron intake -> Nemotron evidence challenge -> Nemotron effect proposal -> server-side policy -> exact predecessor authority -> deterministic gate -> CAS execution -> successor observation -> verification -> accept/recovery`

The NVIDIA model is used materially for a three-stage workflow, not as a cosmetic single call. Authority, successor state, execution, verification, and recovery remain outside the model.

## Frequency gates

| Gate | Status | Evidence |
| --- | --- | --- |
| Competition fit | PASS | Best Apps and Agents is the natural track for a governed autonomous workflow. |
| Required Nebius/NVIDIA use | PASS in implementation | Token Factory OpenAI-compatible runtime and NVIDIA Nemotron models are integrated. Live proof still required. |
| Existing-project substantial update | PASS in design | New provider fleet, provider/model provenance, runtime configuration, tests, and adversarial demo path are competition-period changes. |
| Need != Authority | PASS | Inspector need never grants execution capability. |
| Evidence != Authority | PASS | Evidence is classified before model use and never grants authority. |
| Model != Authority | PASS | Nemotron can only return one policy-named effect proposal. |
| Exact predecessor binding | PASS | Existing revision-bound state and CAS execution remain intact. |
| Execution != Evidence | PASS | Executor receipt is still insufficient for acceptance. |
| Recovery independence | PASS at current scope | Separate recovery authority/evidence remains required. |
| Provider provenance | PASS | Provider, model, and per-run trace ID are written into transition evidence. |
| Secret handling | PASS in repository | API key is environment-only; no real key is committed. |
| Deterministic regression | PASS | 27 tests pass after the Nebius integration. |
| Static QA | PASS | Ruff, compileall, diff check, and repository secret-pattern sweep pass. |
| Live Token Factory proof | BLOCKED | No authenticated Nebius API key has been exercised yet. |
| Submission license | BLOCKED | Main FlowBound is PolyForm Noncommercial; Devpost requires an open-source submission repository. |

## Repository protection decision

Do **not** relicense the main FlowBound repository automatically.

The competition requires a public repository with a recognized open-source license such as Apache-2.0, MIT, or MPL-2.0. The safe route is a separate competition repository containing only the self-contained competition edition required for judging. Frequency internals, unrelated products, private operational material, credentials, and commercial-only components must not be exported.

This keeps the main product boundary intact while satisfying the competition's public-source requirement.

## Live proof checklist

1. Create or provide a Nebius Token Factory API key.
2. Run `scripts/nebius-smoke.py` and capture model-catalog plus inference success.
3. Run a full FlowBound case with `FLOWBOUND_AGENT_MODE=nebius`.
4. Capture the transition record showing provider/model/trace provenance.
5. Run the adversarial evidence case and show pre-model quarantine.
6. Host the demo and verify the public URL.
7. Build the separate open-source competition repository.
8. Record the <=3 minute video only from the live path.

## Current claim boundary

We can claim that the Nebius/Nemotron runtime is implemented and deterministically tested. We cannot yet claim live Token Factory execution, hosted competition deployment, or Devpost submission readiness until the two blocked gates above are cleared.
