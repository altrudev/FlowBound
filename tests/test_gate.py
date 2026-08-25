from flowbound import Decision, TransitionProposal, evaluate_transition


def proposal(**overrides):
    base = dict(
        actor="inspection-action-agent",
        predecessor_state="case:open",
        observed_state="case:open",
        requested_effect="create-remediation-task",
        allowed_effects=frozenset({"create-remediation-task", "schedule-follow-up"}),
        actor_authorities=frozenset({"remediation.write"}),
        required_authority="remediation.write",
        evidence_trusted=True,
        requires_human_approval=False,
        human_approval_present=False,
    )
    base.update(overrides)
    return TransitionProposal(**base)


def test_allows_transition_inside_envelope():
    assert evaluate_transition(proposal()).decision == Decision.ALLOW


def test_rejects_stale_predecessor_state():
    result = evaluate_transition(proposal(observed_state="case:closed"))
    assert result.decision == Decision.REJECT
    assert "stale" in result.reason.lower()


def test_rejects_missing_authority():
    result = evaluate_transition(proposal(actor_authorities=frozenset()))
    assert result.decision == Decision.REJECT
    assert "authority" in result.reason.lower()


def test_rejects_out_of_envelope_effect():
    result = evaluate_transition(proposal(requested_effect="close-building"))
    assert result.decision == Decision.REJECT
    assert "effect envelope" in result.reason.lower()


def test_quarantines_untrusted_evidence():
    result = evaluate_transition(proposal(evidence_trusted=False))
    assert result.decision == Decision.QUARANTINE


def test_escalates_when_human_approval_required():
    result = evaluate_transition(proposal(requires_human_approval=True))
    assert result.decision == Decision.ESCALATE


def test_allows_after_required_human_approval():
    result = evaluate_transition(
        proposal(requires_human_approval=True, human_approval_present=True)
    )
    assert result.decision == Decision.ALLOW
