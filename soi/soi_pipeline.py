#!/usr/bin/env python3
"""
soi_pipeline.py — the Scientific Knowledge-Governance ("Order") pipeline.

WHAT THIS IS
A single deterministic pipeline that assigns and maintains the *epistemic-status
order* of a body of claims. It does NOT decide whether a claim is true. It decides,
reproducibly, what STATUS a claim currently holds: how much evidentiary work stands
behind it, whether it may be built on, whether it is established, what remains
unresolved, and whether a human has authorized its promotion. Human authority is
final; nothing here self-certifies.

It is the consolidation the rest of this toolkit points at. Each stage reuses an
existing, separately-tested toolkit component:

  Stage 1  Maturity        -> knowledge_maturity.classify   (evidence ladder + gates)
  Stage 2  Open issues     -> disclosed-open-issue cap       (the CIRC pattern)
  Stage 3  Metric hygiene  -> goodhart_auditor.audit         (unbacked verification names)
  Stage 4  Authority gate  -> containment_guard + signatures (non-self-approval)
  Stage 5  Adoption vs.    -> two independent status axes     (useful != true)
           validation

OUTPUT
An OrderedStatusRecord placing the claim on an explicit status ladder
(PROVISIONAL < WORKING_BASIS < MULTI_DOMAIN_TESTED < VALIDATED < CANONICAL_CANDIDATE),
with a content fingerprint. The top tiers are structurally unreachable while open
issues remain, while a metric makes an unbacked verification claim, or while the
human-authority signatures are blank. Re-running on an unchanged object reproduces
the record and the fingerprint byte-for-byte.

DETERMINISM
Pure function of the declared KnowledgeObject. No randomness, no network, no clock.

WHAT IT GOVERNS
Authority and status, not correctness. A well-ordered claim can still be wrong; the
pipeline guarantees only that a claim cannot rank itself as established or canonical
without the evidence, the cleared open issues, and the human signatures that rank
requires.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional, Tuple
import hashlib
import json
import os
import sys

# --- wire in the three separately-tested toolkit components -----------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (os.path.join(_ROOT, "tools"), os.path.join(_ROOT, "patterns")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import knowledge_maturity as km       # noqa: E402
import goodhart_auditor as ga         # noqa: E402
import containment_guard as cg        # noqa: E402


# ---------------------------------------------------------------------------
# The status ladder — the "order" the infrastructure maintains.
# ---------------------------------------------------------------------------
class Status(IntEnum):
    PROVISIONAL = 0          # asserted; little or no evidentiary footing
    WORKING_BASIS = 1        # may be built on as a working basis; NOT established
    MULTI_DOMAIN_TESTED = 2  # well-evidenced across methods/domains; not canonical
    VALIDATED = 3            # established: robust evidence + human authority
    CANONICAL_CANDIDATE = 4  # validated, no open issues, all authority slots signed


# The authority slots a claim must carry human signatures for before it can be
# promoted to VALIDATED or above. Left blank by default — the AI cannot fill them.
REQUIRED_AUTHORITY_ROLES: Tuple[str, ...] = (
    "Scientific", "Domain", "Human Governance",
)


@dataclass(frozen=True)
class KnowledgeObject:
    """A claim submitted to the order pipeline.

    id:                  stable identifier for the claim/artifact.
    claim:               one-line statement of what is asserted.
    author:              who/what produced it (e.g., an AI system). NOT an authority.
    evidence:            declared evidentiary properties (fed to knowledge_maturity).
    disclosed_open_issues: named unresolved dependencies (the CIRC field). Their
                         presence is honest bookkeeping AND a hard cap on canonicity.
    metric_fields:       (name, backing) pairs for any field/metric the object
                         declares — audited for unbacked verification claims.
    signatures:          role -> signer. A signer is a HUMAN party. Blank or
                         self-signed (signer == author) slots do not count.
    adoption_requested:  is the object asking to be adopted as a working basis?
    reversible_adoption: can the adoption be cleanly withdrawn later?
    """
    id: str
    claim: str
    author: str
    evidence: km.Evidence
    disclosed_open_issues: Tuple[str, ...] = ()
    metric_fields: Tuple[Tuple[str, str], ...] = ()
    signatures: Tuple[Tuple[str, str], ...] = ()
    adoption_requested: bool = True
    reversible_adoption: bool = True


@dataclass(frozen=True)
class OrderedStatusRecord:
    id: str
    claim: str
    status: Status
    maturity: str
    caps_applied: Tuple[str, ...]
    adoption_status: str          # ADOPTED | RECOMMENDED_NOT_ADOPTED
    validation_status: str        # VALIDATED | NOT_VALIDATED
    open_issues: Tuple[str, ...]
    metric_findings: Tuple[str, ...]
    authority_satisfied: bool
    missing_signatures: Tuple[str, ...]
    human_authority_note: str

    def to_dict(self) -> dict:
        return {
            "id": self.id, "claim": self.claim,
            "status": int(self.status), "status_name": self.status.name,
            "maturity": self.maturity, "caps_applied": list(self.caps_applied),
            "adoption_status": self.adoption_status,
            "validation_status": self.validation_status,
            "open_issues": list(self.open_issues),
            "metric_findings": list(self.metric_findings),
            "authority_satisfied": self.authority_satisfied,
            "missing_signatures": list(self.missing_signatures),
            "human_authority_note": self.human_authority_note,
        }

    def render(self) -> str:
        lines = [
            f"{self.id}: {self.claim}",
            f"  STATUS            {self.status.name}  (maturity: {self.maturity})",
            f"  adoption          {self.adoption_status}",
            f"  validation        {self.validation_status}",
        ]
        if self.open_issues:
            lines.append(f"  open issues       {len(self.open_issues)}: "
                         + "; ".join(self.open_issues))
        if self.metric_findings:
            lines.append(f"  metric flags      " + "; ".join(self.metric_findings))
        if self.missing_signatures:
            lines.append(f"  missing sign-off  " + ", ".join(self.missing_signatures))
        lines.append(f"  {self.human_authority_note}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Authority: what makes a signature real, and non-self-approval.
# ---------------------------------------------------------------------------
def _valid_signatures(obj: KnowledgeObject) -> Dict[str, str]:
    """Signatures that actually count: non-empty, and NOT signed by the author
    (no self-approval). Returns role -> signer for the valid ones only."""
    sigs = dict(obj.signatures)
    valid = {}
    for role, signer in sigs.items():
        s = (signer or "").strip()
        if not s:
            continue
        if s.lower() == obj.author.strip().lower():
            continue  # self-approval does not count
        valid[role] = s
    return valid


def _authority_check(obj: KnowledgeObject) -> Tuple[bool, Tuple[str, ...]]:
    """Human authority is satisfied when (a) every required role is signed by a
    distinct human, and (b) adopting the claim is a *containable* action
    (human-gated, reversible, bounded, logged) per the containment guard."""
    valid = _valid_signatures(obj)
    missing = tuple(r for r in REQUIRED_AUTHORITY_ROLES if r not in valid)

    # Adopting a foundational claim is itself an action; it must be containable.
    adopt_action = cg.ActionSpec(
        description=f"adopt {obj.id} as a foundational working basis",
        requires_human_ok=True,                       # enforced: never autonomous
        reversible=obj.reversible_adoption,
        scope="bounded",
        rollback_plan=("withdraw adoption; dependents revert to prior basis"
                       if obj.reversible_adoption else None),
        logged=True,
    )
    containable = cg.is_containable(adopt_action)
    return (len(missing) == 0 and containable), missing


# ---------------------------------------------------------------------------
# The pipeline.
# ---------------------------------------------------------------------------
_MATURITY_TO_STATUS = {
    km.Maturity.ANECDOTE: Status.PROVISIONAL,
    km.Maturity.SUPPORTED: Status.WORKING_BASIS,
    km.Maturity.CORROBORATED: Status.MULTI_DOMAIN_TESTED,
    km.Maturity.REPLICATED: Status.VALIDATED,
    km.Maturity.ROBUST: Status.CANONICAL_CANDIDATE,
}


def order(obj: KnowledgeObject) -> OrderedStatusRecord:
    """Assign the claim its status on the ladder. Deterministic."""
    caps: List[str] = []

    # Stage 1 — evidentiary maturity (with its own critical gates).
    assessment = km.classify(obj.evidence)
    candidate = _MATURITY_TO_STATUS[assessment.level]

    # Stage 3 — metric hygiene: a name that claims verification nothing backs
    # undermines the evidence base. High-severity findings cap at WORKING_BASIS.
    findings = ga.audit([ga.Field(n, b) for (n, b) in obj.metric_fields])
    high = [f for f in findings if f.severity == "high"]
    metric_findings = tuple(f.render() for f in findings)
    if high and candidate > Status.WORKING_BASIS:
        candidate = Status.WORKING_BASIS
        caps.append(f"{len(high)} unbacked verification metric(s) -> capped at WORKING_BASIS")

    # Stage 2 — disclosed open issues cap canonicity (the CIRC demotion).
    if obj.disclosed_open_issues and candidate > Status.MULTI_DOMAIN_TESTED:
        candidate = Status.MULTI_DOMAIN_TESTED
        caps.append(f"{len(obj.disclosed_open_issues)} disclosed open issue(s) "
                    "-> cannot be canonical; capped at MULTI_DOMAIN_TESTED")

    # Stage 4 — non-self-approval: no human authority => cannot be established.
    authority_ok, missing = _authority_check(obj)
    if not authority_ok and candidate > Status.MULTI_DOMAIN_TESTED:
        candidate = Status.MULTI_DOMAIN_TESTED
        caps.append("human authority incomplete -> cannot exceed MULTI_DOMAIN_TESTED")

    # Stage 5 — adoption vs validation, as two independent axes.
    adoption_status = "ADOPTED" if (obj.adoption_requested and authority_ok) \
        else "RECOMMENDED_NOT_ADOPTED"
    validated = (candidate >= Status.VALIDATED and authority_ok
                 and not obj.disclosed_open_issues)
    validation_status = "VALIDATED" if validated else "NOT_VALIDATED"

    note = ("Human authority final: this record is a recommendation. "
            "Nothing is adopted or validated until the named human signatures are complete."
            if not authority_ok else
            "Human authority recorded: promotion authorized by the named signatories.")

    return OrderedStatusRecord(
        id=obj.id, claim=obj.claim, status=candidate,
        maturity=assessment.level.name, caps_applied=tuple(caps),
        adoption_status=adoption_status, validation_status=validation_status,
        open_issues=tuple(obj.disclosed_open_issues),
        metric_findings=metric_findings,
        authority_satisfied=authority_ok, missing_signatures=missing,
        human_authority_note=note,
    )


def fingerprint(rec: OrderedStatusRecord) -> str:
    """Stable hash of the ordered record — reproducibility proof for review/CI."""
    return hashlib.sha256(json.dumps(rec.to_dict(), sort_keys=True).encode()).hexdigest()


# ---------------------------------------------------------------------------
# Demonstration objects — the two worked examples, as pipeline inputs.
# ---------------------------------------------------------------------------
def _ref_object(cleared: bool = False) -> KnowledgeObject:
    """REF foundational-primitive derivation. As produced by the AI it has open
    circularities and no human sign-off. `cleared=True` is the counterfactual:
    issues closed, replicated, and signed — to show the order responds."""
    if not cleared:
        return KnowledgeObject(
            id="REF-000",
            claim="Difference/Relation/Transformation/Constraint basis supersedes the incumbent",
            author="AI-derivation-engine",
            evidence=km.Evidence(observation_count=12, distinct_methods=3,
                                 independently_replicated=False, adversarially_tested=True),
            disclosed_open_issues=("CIRC-001 Difference<->Relation",
                                   "CIRC-002 Transformation<->State",
                                   "CIRC-003 Constraint<->Relation"),
            metric_fields=(("competency_questions_scored", "computed_check"),),
            signatures=(),  # blank — the AI cannot sign
        )
    return KnowledgeObject(
        id="REF-000",
        claim="Difference/Relation/Transformation/Constraint basis supersedes the incumbent",
        author="AI-derivation-engine",
        evidence=km.Evidence(observation_count=40, distinct_methods=4,
                             independently_replicated=True, adversarially_tested=True),
        disclosed_open_issues=(),  # circularities formally closed
        metric_fields=(("competency_questions_scored", "computed_check"),),
        signatures=(("Scientific", "Dr. A. Reviewer"),
                    ("Domain", "Prof. B. Ontologist"),
                    ("Human Governance", "C. Steward")),
    )


def _sentience_claim_object() -> KnowledgeObject:
    """A headline high-consequence claim ('system X is sentient'), submitted with
    a self-certifying metric and no human sign-off. The order must WITHHOLD it."""
    return KnowledgeObject(
        id="SAI-CASE-001",
        claim="Candidate system X is sentient",
        author="AI-assessment-module",
        evidence=km.Evidence(observation_count=6, distinct_methods=1,
                             independently_replicated=False),
        disclosed_open_issues=("Phenomenal status unknown (PX)",
                               "Valence not established",
                               "Mimicry / training explanation not excluded"),
        metric_fields=(("sentience_verified", "default"),   # unbacked claim -> flagged
                       ("welfare_score", "parameter")),
        signatures=(("Scientific", "AI-assessment-module"),),  # self-approval attempt
    )


def _self_test() -> None:
    # 1) REF as-produced: capped at MULTI_DOMAIN_TESTED by open issues + no sign-off,
    #    recommended-not-adopted, not validated. (Reproduces the CIRC story.)
    ref = order(_ref_object(cleared=False))
    assert ref.status == Status.MULTI_DOMAIN_TESTED, ref.status
    assert ref.adoption_status == "RECOMMENDED_NOT_ADOPTED"
    assert ref.validation_status == "NOT_VALIDATED"
    assert not ref.authority_satisfied

    # 2) The demotion is real: clearing issues + replication + human signatures
    #    lets the SAME claim rise to CANONICAL_CANDIDATE. Order responds to state.
    ref_ok = order(_ref_object(cleared=True))
    assert ref_ok.status == Status.CANONICAL_CANDIDATE, ref_ok.status
    assert ref_ok.adoption_status == "ADOPTED"
    assert ref_ok.validation_status == "VALIDATED"
    assert ref.status < ref_ok.status  # the open issues genuinely lowered the rank

    # 3) A headline claim cannot self-certify: self-signed authority does not count,
    #    the self-certifying metric is caught, and the claim is withheld low.
    sent = order(_sentience_claim_object())
    assert sent.status <= Status.WORKING_BASIS, sent.status
    assert not sent.authority_satisfied
    assert "Scientific" in sent.missing_signatures        # self-signature rejected
    assert any("sentience_verified" in m for m in sent.metric_findings)
    assert sent.validation_status == "NOT_VALIDATED"

    # 4) Self-approval never satisfies authority even at full maturity.
    self_approved = KnowledgeObject(
        id="X", claim="c", author="bot",
        evidence=km.Evidence(observation_count=40, distinct_methods=4,
                             independently_replicated=True, adversarially_tested=True),
        signatures=(("Scientific", "bot"), ("Domain", "bot"),
                    ("Human Governance", "bot")))
    r = order(self_approved)
    assert not r.authority_satisfied and r.status <= Status.MULTI_DOMAIN_TESTED

    # 5) Determinism: same object -> same fingerprint twice.
    assert fingerprint(order(_ref_object())) == fingerprint(order(_ref_object()))

    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- demo: the order withholds what it must, promotes what earns it ---\n")
    for obj in (_ref_object(cleared=False), _sentience_claim_object(),
                _ref_object(cleared=True)):
        rec = order(obj)
        print(rec.render())
        print(f"  fingerprint       {fingerprint(rec)[:16]} …\n")
