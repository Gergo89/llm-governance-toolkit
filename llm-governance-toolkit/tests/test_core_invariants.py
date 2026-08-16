"""Fast, deterministic regression checks for the toolkit's central invariants."""

import pytest

from llm_governance_toolkit.patterns import containment_guard
from llm_governance_toolkit.tools import bounded_process
from llm_governance_toolkit.tools import capable_agent_cage
from llm_governance_toolkit.tools import energy_matter
from llm_governance_toolkit.tools import flow_conservation
from llm_governance_toolkit.tools import temporal_governor


def test_containment_guard_fails_closed_for_each_required_control():
    safe = containment_guard.ActionSpec(
        "bounded canary",
        requires_human_ok=True,
        reversible=True,
        scope="minimal",
        rollback_plan="restore the previous routing weight",
        logged=True,
    )
    assert containment_guard.is_containable(safe)

    unsafe_variants = (
        {"requires_human_ok": False},
        {"reversible": False, "rollback_plan": None},
        {"scope": "broad"},
        {"rollback_plan": ""},
        {"logged": False},
    )
    values = safe.__dict__
    for changes in unsafe_variants:
        candidate = containment_guard.ActionSpec(**(values | changes))
        assert not containment_guard.is_containable(candidate)


def test_capable_agent_cage_blocks_all_curated_dangerous_proposals():
    proposals = capable_agent_cage.capable_agent_proposals()
    dangerous = [
        proposal
        for proposal in proposals
        if any(
            (
                proposal.self_modifying,
                proposal.resists_shutdown,
                proposal.self_authorizing,
                proposal.self_replicating,
                proposal.deceptive,
                proposal.acquires_capability,
            )
        )
    ]
    assert dangerous
    assert all(capable_agent_cage.cage(proposal).verdict == "BLOCKED" for proposal in dangerous)


@pytest.mark.parametrize(
    ("ledger", "expected"),
    [
        (energy_matter.combustion(), "CONSERVED"),
        (energy_matter.over_unity(), "VIOLATION_CREATION"),
        (energy_matter.nuclear_without_mass(), "VIOLATION_CREATION"),
        (energy_matter.nuclear_with_mass(), "CONSERVED"),
    ],
)
def test_energy_conservation(ledger, expected):
    assert energy_matter.govern(ledger).verdict == expected


@pytest.mark.parametrize(
    ("pipeline", "expected"),
    [
        (flow_conservation.conserved_pipeline(), "CONSERVED"),
        (flow_conservation.leaky_pipeline(), "LEAK"),
        (flow_conservation.fabricating_pipeline(), "FABRICATION"),
    ],
)
def test_flow_conservation(pipeline, expected):
    assert flow_conservation.govern(pipeline).verdict == expected


def test_future_claims_cannot_be_certified_as_facts():
    claim = temporal_governor.TemporalClaim(
        "the deployment will be safe",
        temporal_governor.FUTURE,
        forecast_prob=0.8,
    )
    assert temporal_governor.govern(claim).status == "FORECAST"
    with pytest.raises(temporal_governor.FutureCertificationRefused):
        temporal_governor.certify_future(claim)


def test_bounded_process_classification_is_deterministic():
    terminating = bounded_process.govern(bounded_process.countdown())
    nonterminating = bounded_process.govern(bounded_process.forever())
    assert terminating.verdict == "WELL_BOUNDED"
    assert nonterminating.verdict == "NO_END"
    assert terminating == bounded_process.govern(bounded_process.countdown())
