# FlowBound DDC Architecture Review — 2026-08-26

## Review basis

- **DDC canonical registry:** `altrudev/ddc/docs/DDC-STANDING-PRINCIPLES.md`
- **Registry commit:** `376e5d75d2a6cdef557eb8acccfd24cfba238ec8`
- **FlowBound implementation reviewed through:** `b0186510e031d4141aa9b53d5d4aaf02fdca4bcd`
- **Scope:** Google All Things Agentic Hackathon vertical slice: ADK/Gemini proposal fleet → FlowBound Gate → revision-bound execution → Firestore/Pub/Sub evidence → successor verification.
- **Test evidence:** 22/22 deterministic local tests passed against the equivalent reviewed source, including legacy gate/adapter tests, stale-state races, authority mismatch, quarantine, executor-claim independence, and transition-lineage checks.

## Disposition

**STAGE / ACCEPT FOR GOOGLE CLOUD INTEGRATION TESTING. NOT YET ACCEPTED AS FINAL PRODUCTION ASSURANCE.**

The core transition design is materially stronger after DDC review. Two assurance dependencies remain unresolved and must not be described as solved in the final submission until evidence exists: independent evidence-trust classification and stronger failure-path independence for successor verification.

## Standing gate results

| DDC principle / gate | Status | Evidence / reasoning |
| --- | --- | --- |
| Need ≠ Authority | PASS | The inspector observation and model rationale are preserved as evidence/lineage but do not grant tool authority. Server-side actor authorities and policy rules determine the permitted effect. |
| Data / Evidence ≠ Authority | PASS with dependency | Agent prompts explicitly treat retrieved material as evidence rather than instructions, and the gate never derives authority from evidence. The *source of the `evidence_trusted` classification* remains unresolved; see below. |
| Execution ≠ Evidence | PASS | An executor receipt is not treated as proof of success. The system re-reads state and verifies the successor. A regression test uses a deliberately lying executor and correctly produces verification failure. |
| Authentic state ≠ Current authorized state | PASS | Predecessor identity includes `state@revision`; the state is re-read after model reasoning and Firestore execution uses transactional compare-and-set. |
| Retry ≠ Recovery | PASS at current scope | Verification failure sets a recovery-required block rather than silently retrying or accepting the transition. No automatic recovery promotion exists. |
| Semantic propagation / ambiguity | PASS | Effects are named and bounded by server-side policy rules. Unknown effects are rejected; state-inapplicable effects fall outside the permitted effect envelope. |
| Layer Contribution Test | PASS | ADK/Gemini provide reasoning/orchestration; Firestore provides durable state; Pub/Sub provides asynchronous events. FlowBound adds a separately testable property: deterministic state/authority-bound transition authorization and successor acceptance. |
| Non-Redundant Build Principle | PASS | FlowBound does not replace ADK orchestration, Google persistence, queues, or model serving. Custom code is narrowed to the unresolved governance property and its evidence path. |
| Failure-Path Independence Principle | UNRESOLVED | The verifier does not inherit the executor's claimed receipt and has a distinct read/compare path. However, executor and verifier still share the FlowBound process and the same case-state store. A compromised/corrupted shared store could create correlated failure. |
| Explicit authority | PASS | Effect rules map to named required authorities; the model cannot mint authorities in its structured output. |
| Exact predecessor state | PASS | `StateSnapshot(state, revision)` forms the predecessor token. A state change during model reasoning is rejected, even if the human-readable state label would otherwise appear plausible. |
| Execution boundary | PASS for current case-state effect | Execution is a policy-derived compare-and-set transition, not arbitrary model-provided code or successor state. |
| Independent postcondition / successor verification | PARTIAL | Verification independently observes state rather than trusting the executor receipt and checks both successor label and exact next revision. Infrastructure independence remains unresolved because the same store is authoritative for execution and observation. |
| Invariant preservation | PASS for current state machine | Policy defines predecessor → effect → successor. Verification rejects wrong successor state or revision. |
| Evidence and lineage | PASS for current slice | Transition records preserve policy version, originating need, agent rationale, evidence IDs, authority context, decision, execution receipt, verification, and event sequence. |
| Explicit transition acceptance / recovery | PASS | Successful verification emits `flowbound.transition.accepted`; failure emits `flowbound.transition.recovery_required` and blocks subsequent case execution pending recovery. |
| Recovery independence invariant | PARTIAL / UNRESOLVED | A failed transition cannot promote itself; the case is blocked. An independent recovery-evidence and unblocking mechanism is not yet implemented, so recovery itself is intentionally unavailable rather than self-authorized. |
| Core ≠ System | PASS in claims discipline | This review applies to the current transition slice only. It does not claim that Google Cloud deployment, Model Armor, agent identity, or the final product are already assured. |

## New properties introduced by this build

1. **Revision-bound authorization:** authorization is tied to the exact predecessor revision, not just a state label.
2. **Policy-owned successor:** the model proposes an effect name; server-side policy determines authority and successor state.
3. **Atomic execution guard:** the state mutation uses compare-and-set semantics; Firestore uses a transaction.
4. **Receipt-independent verification:** successful executor return values do not establish completion.
5. **Explicit acceptance:** a transition is accepted only after observed successor conformance.
6. **Fail-closed recovery block:** verification failure stops further case progression instead of silently continuing.
7. **Need/rationale provenance:** originating observation and model rationale are retained as evidence but do not become authority.

## Unresolved dependencies before final assurance claim

### U1 — Evidence-trust provenance

Current demo/API flow can provide the `evidence_trusted` classification. This is suitable for deterministic testing but is **not sufficient for the final adversarial demo or production claim**. The cloud path should derive this from an independent security boundary (for example Model Armor plus deterministic input policy) and preserve that classifier's evidence/provenance.

**Required disposition:** redesign/integrate before claiming prompt-injection protection.

### U2 — Verifier failure-path correlation

The successor verifier is logically independent from the executor receipt, but execution and observation share the same process and Firestore state domain. One defect or compromised shared dependency could affect both.

**Required disposition:** stage. For the hackathon, add at minimum a separately structured verification/evidence path; for stronger production assurance, place verification evidence across a meaningfully independent failure domain.

### U3 — Recovery authority

Recovery is correctly blocked, but no independent recovery authority/evidence path has been implemented. That is safer than self-recovery but incomplete.

**Required disposition:** keep blocked until an independent recovery workflow exists.

### U4 — Cloud execution evidence

The Cloud Run deployment configuration is present, but this review does not treat configuration as deployment evidence. Gemini/ADK, Firestore, Pub/Sub, and Cloud Run must be exercised using the authenticated Google Cloud project and captured in runtime traces before final submission claims.

**Required disposition:** require evidence.

## DDC conclusion

The vertical slice is accepted for deployment-stage testing because it now preserves the core chain:

`originating need → server-side authority/policy → exact predecessor revision → model-proposed effect → deterministic gate → atomic execution → independently observed successor → invariant check → explicit acceptance or recovery block → evidence lineage`

The build must remain staged until U1–U4 are addressed or accurately disclosed.
