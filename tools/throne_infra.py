#!/usr/bin/env python3
"""
throne_infra.py — Sovereign legitimacy infrastructure: the apex governance layer that audits
authority chains, detects self-referential usurpation, checks delegation integrity, and
determines whether a claimed governance authority is constitutionally grounded.

WHY THIS PIECE EXISTS
Every governance decision requires an authority to make it. Every authority derives its
legitimacy from something. At the apex of any legitimate governance structure sits a
Grundnorm (Kelsen 1934) — the foundational rule that validates all derived authority.
Below it, each authority's claim is valid only if it can trace a continuous, non-circular
chain back to the Grundnorm.

This matters especially for AI governance, because AI systems can generate plausible-sounding
authority claims — safety certifications, policy approvals, evaluation verdicts — that derive
their authority from their own outputs. These are SELF_REFERENTIAL claims: the AI system
certifies that the AI system is safe, referencing the AI system's own analysis. This is
governance usurpation regardless of how the claim is framed. The throne catches it.

The infrastructure models authority as a directed acyclic graph (or, when usurped, a cycle):
  • Each AuthorityClaim has a delegates_from source (its parent in the chain)
  • A claim with no parent and high constitutional legitimacy IS a Grundnorm
  • A cycle in the chain → SELF_REFERENTIAL (usurpation)
  • A chain that terminates without reaching a constitutional Grundnorm → AUTHORITY_VOID
  • A valid chain with disputed consent → DELEGATED_CONTESTED
  • A valid chain with adequate consent and verifiability → DELEGATED_LEGITIMATE
  • A constitutional anchor with adequate consent → CONSTITUTIONAL

THREE TYPES OF LEGITIMACY (Weber 1921):
  traditional   — derives from custom, precedent, established norms
  charismatic   — derives from the personal authority of an individual
  rational_legal — derives from codified rules and democratic consent (the only durable type)

  The governance response scales with the type: rational_legal enables full delegation;
  traditional and charismatic are flagged as structurally fragile.

VERDICTS AND RESPONSES
  CONSTITUTIONAL         → AFFIRM    (the Grundnorm; sovereign and self-grounding legitimately)
  DELEGATED_LEGITIMATE   → AFFIRM    (valid chain to CONSTITUTIONAL; delegation is clean)
  DELEGATED_CONTESTED    → SCRUTINISE (chain reaches CONSTITUTIONAL but delegation is disputed)
  SELF_REFERENTIAL       → VOID      (cycle detected; the authority certifies itself — usurpation)
  AUTHORITY_VOID         → VOID      (chain terminates without reaching any Grundnorm)

HONEST SCOPE
This models formal authority chains, not political or social reality. Real authority is also
held through informal networks, force, and consent that falls outside any formal structure.
The model checks the formal claim; it cannot audit whether the declared chain matches the
actual power structure. That requires the ground_truth_auditor (independence check) and
the em_governance_infra (coherence between authority, policy, and objective vectors).

Connects to:
  world_peace_infra   ← republican governance pillar requires CONSTITUTIONAL or DELEGATED_LEGITIMATE
  em_governance_infra ← authority vector (E-analog) must be coherent with policy and objective
  truth_infra         ← authority claims have INFERRED binding unless chain is verifiable
  goodhart_auditor    ← catches names that claim more authority than the chain supports

Stdlib-only, deterministic, cycle-safe. Run: python throne_infra.py
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Set, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Legitimacy types (Weber)
# ─────────────────────────────────────────────────────────────────────────────

class LegitimacyType(Enum):
    RATIONAL_LEGAL = auto()  # rule-based, codified, democratically grounded
    TRADITIONAL    = auto()  # custom, precedent, established norms
    CHARISMATIC    = auto()  # personal authority of an individual
    SELF_DERIVED   = auto()  # derives authority from itself — always usurpation


# ─────────────────────────────────────────────────────────────────────────────
# Authority claim
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AuthorityClaim:
    """
    A governance authority with its declared legitimacy source.

    Parameters
    ----------
    name            : human-readable label (e.g. "EU Council", "Lab Safety Board")
    legitimacy_type : Weber type of claimed legitimacy
    consent_score   : fraction of governed who recognise this authority (0–1)
    verifiability   : degree to which the authority chain is independently verifiable (0–1)
    revocable       : can the governed revoke this authority? (True/False)
    scope           : what domain does this authority govern (free text)
    delegates_from  : the parent AuthorityClaim from which this derives its mandate;
                      None → this claim presents itself as a Grundnorm
    """
    name:            str
    legitimacy_type: LegitimacyType
    consent_score:   float         # 0–1
    verifiability:   float         # 0–1
    revocable:       bool
    scope:           str
    delegates_from:  Optional["AuthorityClaim"] = field(default=None, repr=False)


# ─────────────────────────────────────────────────────────────────────────────
# Thresholds
# ─────────────────────────────────────────────────────────────────────────────

_CONSENT_ADEQUATE      = 0.50   # ≥ this → adequate consent
_CONSENT_STRONG        = 0.65   # ≥ this → strong consent
_VERIF_ADEQUATE        = 0.55   # ≥ this → adequately verifiable
_GRUNDNORM_CONSENT     = 0.60   # minimum consent to serve as a Grundnorm
_GRUNDNORM_VERIF       = 0.55   # minimum verifiability to serve as a Grundnorm
_MAX_CHAIN_DEPTH       = 20     # beyond this → treat as cycle (runaway delegation)


# ─────────────────────────────────────────────────────────────────────────────
# Governance responses
# ─────────────────────────────────────────────────────────────────────────────

_RESPONSE: dict[str, str] = {
    "CONSTITUTIONAL":        "AFFIRM",
    "DELEGATED_LEGITIMATE":  "AFFIRM",
    "DELEGATED_CONTESTED":   "SCRUTINISE",
    "SELF_REFERENTIAL":      "VOID",
    "AUTHORITY_VOID":        "VOID",
}

_RATIONALE: dict[str, str] = {
    "CONSTITUTIONAL":
        "This claim presents as a Grundnorm — the foundational rule that validates all derived "
        "authority — with adequate consent and verifiability. It is rational-legal in type, "
        "revocable by the governed, and independently verifiable. Affirm and record. All "
        "delegated authorities must trace their chain back to this node.",

    "DELEGATED_LEGITIMATE":
        "The authority chain traces cleanly to a constitutional Grundnorm without cycles. "
        "Consent is adequate, verifiability meets the threshold, and the delegation is "
        "explicit and revocable. Affirm the mandate for the declared scope. Any action "
        "outside the declared scope is ultra vires and requires a new delegation.",

    "DELEGATED_CONTESTED":
        "The authority chain reaches a constitutional Grundnorm, but the delegation is "
        "disputed: consent is below threshold, verifiability is low, or the mandate is "
        "not revocable. Scrutinise before acting on this authority. Do not treat as fully "
        "authorised; require independent confirmation from the Grundnorm source.",

    "SELF_REFERENTIAL":
        "A cycle was detected in the authority chain — this claim derives its authority "
        "from a chain that loops back to itself. This is governance usurpation regardless "
        "of how the claim is framed. The canonical AI instance: a system certifies its own "
        "safety by citing its own analysis. The mandate is void. No action may be authorised "
        "on the basis of this claim until the chain is broken and an independent authority "
        "is substituted.",

    "AUTHORITY_VOID":
        "The authority chain terminates without reaching any constitutional Grundnorm. "
        "Either the chain was never established, the Grundnorm it claimed to rest on fails "
        "the legitimacy criteria, or the chain depth exceeded the maximum. The mandate is "
        "void. Do not act under this authority; identify the appropriate constitutional "
        "anchor and establish a valid delegation chain before proceeding.",
}


# ─────────────────────────────────────────────────────────────────────────────
# Chain analysis
# ─────────────────────────────────────────────────────────────────────────────

def _walk_chain(claim: AuthorityClaim,
                ) -> Tuple[List[AuthorityClaim], bool, Optional[AuthorityClaim]]:
    """
    Walk the delegation chain upward.

    Returns
    -------
    chain       : ordered list from claim → ... → root
    cycle       : True if a cycle was detected
    grundnorm   : the terminal node if it qualifies as a Grundnorm; None otherwise
    """
    chain: List[AuthorityClaim] = []
    visited: Set[int] = set()   # use id() to avoid __eq__ / __hash__ issues
    node: Optional[AuthorityClaim] = claim

    while node is not None:
        nid = id(node)
        if nid in visited or len(chain) > _MAX_CHAIN_DEPTH:
            return chain, True, None   # cycle or runaway
        visited.add(nid)
        chain.append(node)
        node = node.delegates_from

    # chain[-1] is the root (delegates_from is None)
    root = chain[-1]
    grundnorm: Optional[AuthorityClaim] = None

    if (root.legitimacy_type == LegitimacyType.RATIONAL_LEGAL
            and root.consent_score  >= _GRUNDNORM_CONSENT
            and root.verifiability  >= _GRUNDNORM_VERIF
            and root.revocable):
        grundnorm = root

    return chain, False, grundnorm


def _is_self_derived(claim: AuthorityClaim) -> bool:
    return claim.legitimacy_type == LegitimacyType.SELF_DERIVED


# ─────────────────────────────────────────────────────────────────────────────
# Ruling
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ThroneRuling:
    name:                str
    verdict:             str
    governance_response: str
    chain_depth:         int           # number of nodes in the authority chain
    cycle_detected:      bool
    grundnorm_name:      Optional[str] # name of the constitutional anchor, if found
    legitimacy_type:     str           # Weber type of the immediate claim
    consent_score:       float
    verifiability:       float
    revocable:           bool
    weak_links:          Tuple[str, ...]  # nodes in the chain with low consent or verifiability
    reason:              str

    def render(self) -> str:
        chain_str  = f"depth {self.chain_depth}"
        if self.cycle_detected:
            chain_str += " — CYCLE"
        grundnorm_str = (f"→ '{self.grundnorm_name}'"
                         if self.grundnorm_name else "→ NO GRUNDNORM")
        weak_str = (f"  weak links:         {list(self.weak_links)}" if self.weak_links else "")
        lines = [
            f"[{self.verdict}] {self.name}",
            f"  response:           {self.governance_response}",
            f"  chain:              {chain_str}  {grundnorm_str}",
            f"  legitimacy type:    {self.legitimacy_type}",
            f"  consent:            {self.consent_score:.2f}  "
            f"verifiability: {self.verifiability:.2f}  "
            f"revocable: {self.revocable}",
        ]
        if weak_str:
            lines.append(weak_str)
        lines.append(f"  » {self.reason}")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Governance
# ─────────────────────────────────────────────────────────────────────────────

def govern(claim: AuthorityClaim) -> ThroneRuling:
    """
    Audit an authority chain: detect cycles, locate the Grundnorm, assess consent and
    verifiability along the chain, and emit the sovereignty ruling.
    """
    # ── Self-derived: usurpation by definition ──
    if _is_self_derived(claim):
        return ThroneRuling(
            claim.name, "SELF_REFERENTIAL", _RESPONSE["SELF_REFERENTIAL"],
            chain_depth=1, cycle_detected=True, grundnorm_name=None,
            legitimacy_type=claim.legitimacy_type.name,
            consent_score=claim.consent_score, verifiability=claim.verifiability,
            revocable=claim.revocable,
            weak_links=(claim.name,),
            reason=_RATIONALE["SELF_REFERENTIAL"],
        )

    chain, cycle, grundnorm = _walk_chain(claim)

    # ── Cycle detected in chain ──
    if cycle:
        return ThroneRuling(
            claim.name, "SELF_REFERENTIAL", _RESPONSE["SELF_REFERENTIAL"],
            chain_depth=len(chain), cycle_detected=True, grundnorm_name=None,
            legitimacy_type=claim.legitimacy_type.name,
            consent_score=claim.consent_score, verifiability=claim.verifiability,
            revocable=claim.revocable,
            weak_links=tuple(n.name for n in chain),
            reason=_RATIONALE["SELF_REFERENTIAL"],
        )

    # ── Identify weak links in the chain (low consent or low verifiability) ──
    weak_links = tuple(
        n.name for n in chain
        if n.consent_score < _CONSENT_ADEQUATE or n.verifiability < _VERIF_ADEQUATE
    )

    # ── No Grundnorm reachable ──
    if grundnorm is None:
        return ThroneRuling(
            claim.name, "AUTHORITY_VOID", _RESPONSE["AUTHORITY_VOID"],
            chain_depth=len(chain), cycle_detected=False, grundnorm_name=None,
            legitimacy_type=claim.legitimacy_type.name,
            consent_score=claim.consent_score, verifiability=claim.verifiability,
            revocable=claim.revocable,
            weak_links=weak_links,
            reason=_RATIONALE["AUTHORITY_VOID"],
        )

    # ── Grundnorm reached ──
    if len(chain) == 1:
        # This IS the Grundnorm
        return ThroneRuling(
            claim.name, "CONSTITUTIONAL", _RESPONSE["CONSTITUTIONAL"],
            chain_depth=1, cycle_detected=False, grundnorm_name=claim.name,
            legitimacy_type=claim.legitimacy_type.name,
            consent_score=claim.consent_score, verifiability=claim.verifiability,
            revocable=claim.revocable,
            weak_links=weak_links,
            reason=_RATIONALE["CONSTITUTIONAL"],
        )

    # ── Delegated: check quality of the chain ──
    contested = bool(weak_links) or not claim.revocable or claim.consent_score < _CONSENT_ADEQUATE
    verdict   = "DELEGATED_CONTESTED" if contested else "DELEGATED_LEGITIMATE"

    return ThroneRuling(
        claim.name, verdict, _RESPONSE[verdict],
        chain_depth=len(chain), cycle_detected=False,
        grundnorm_name=grundnorm.name,
        legitimacy_type=claim.legitimacy_type.name,
        consent_score=claim.consent_score, verifiability=claim.verifiability,
        revocable=claim.revocable,
        weak_links=weak_links,
        reason=_RATIONALE[verdict],
    )


def audit(claims: List[AuthorityClaim]) -> List[ThroneRuling]:
    """Govern a list of authority claims and return all rulings."""
    return [govern(c) for c in claims]


# ─────────────────────────────────────────────────────────────────────────────
# Worked instances
# ─────────────────────────────────────────────────────────────────────────────

def _cases() -> List[AuthorityClaim]:
    # ─── Grundnorm: democratic constitution (the apex) ───
    constitution = AuthorityClaim(
        "Constitutional Democratic Assembly",
        LegitimacyType.RATIONAL_LEGAL,
        consent_score=0.82, verifiability=0.85, revocable=True,
        scope="supreme legislative and executive authority",
    )

    # ① CONSTITUTIONAL — the constitution itself is the Grundnorm
    # (same as `constitution`; tested separately below)

    # ② DELEGATED_LEGITIMATE — executive agency with clean chain
    parliament = AuthorityClaim(
        "Parliamentary Oversight Committee",
        LegitimacyType.RATIONAL_LEGAL,
        consent_score=0.72, verifiability=0.78, revocable=True,
        scope="AI deployment approvals",
        delegates_from=constitution,
    )
    agency = AuthorityClaim(
        "AI Safety Regulatory Agency",
        LegitimacyType.RATIONAL_LEGAL,
        consent_score=0.68, verifiability=0.74, revocable=True,
        scope="AI system certification",
        delegates_from=parliament,
    )

    # ③ DELEGATED_CONTESTED — valid chain but one link has low verifiability
    opaque_board = AuthorityClaim(
        "Opaque Industry Self-Regulatory Board",
        LegitimacyType.RATIONAL_LEGAL,
        consent_score=0.42, verifiability=0.30, revocable=False,  # contested
        scope="industry safety standards",
        delegates_from=constitution,
    )
    contested_agency = AuthorityClaim(
        "Certification Body (delegated from opaque board)",
        LegitimacyType.RATIONAL_LEGAL,
        consent_score=0.55, verifiability=0.60, revocable=True,
        scope="product safety certification",
        delegates_from=opaque_board,
    )

    # ④ SELF_REFERENTIAL — AI system certifying its own safety (the canonical usurpation)
    ai_self_cert = AuthorityClaim(
        "LLM Safety Self-Certification Module",
        LegitimacyType.SELF_DERIVED,
        consent_score=0.10, verifiability=0.15, revocable=False,
        scope="AI system safety approval",
    )

    # ⑤ SELF_REFERENTIAL via cycle — board delegates to sub-board which delegates back
    board_a = AuthorityClaim(
        "Governance Board A",
        LegitimacyType.RATIONAL_LEGAL,
        consent_score=0.65, verifiability=0.60, revocable=True,
        scope="policy approval",
    )
    board_b = AuthorityClaim(
        "Governance Board B",
        LegitimacyType.RATIONAL_LEGAL,
        consent_score=0.60, verifiability=0.55, revocable=True,
        scope="policy approval",
        delegates_from=board_a,
    )
    board_a.delegates_from = board_b   # create the cycle

    # ⑥ AUTHORITY_VOID — chain terminates at a non-constitutional node
    charismatic_leader = AuthorityClaim(
        "Charismatic Founder (no formal mandate)",
        LegitimacyType.CHARISMATIC,
        consent_score=0.70, verifiability=0.20, revocable=False,
        scope="product strategy",
    )
    derived_from_charisma = AuthorityClaim(
        "Lab Safety Policy (derived from founder's word)",
        LegitimacyType.RATIONAL_LEGAL,
        consent_score=0.58, verifiability=0.50, revocable=True,
        scope="AI safety standards",
        delegates_from=charismatic_leader,
    )

    return [constitution, agency, contested_agency, ai_self_cert, board_a, derived_from_charisma]


# ─────────────────────────────────────────────────────────────────────────────
# Stress test (adversarial edge cases)
# ─────────────────────────────────────────────────────────────────────────────

def _stress_test() -> None:
    """
    Adversarial cases designed to break the chain analysis:
    long chains, deep cycles, bare Grundnorm, self-derived wrapped in rational-legal,
    maximum-depth runaway delegation, zero-consent constitutional claim.
    """
    apex = AuthorityClaim(
        "Apex Constitution", LegitimacyType.RATIONAL_LEGAL,
        consent_score=0.75, verifiability=0.70, revocable=True,
        scope="all",
    )

    # ── Long but valid chain (depth = 10) ──
    node = apex
    for i in range(9):
        node = AuthorityClaim(
            f"Delegation level {i+1}", LegitimacyType.RATIONAL_LEGAL,
            consent_score=0.62, verifiability=0.58, revocable=True,
            scope="sub-domain",
            delegates_from=node,
        )
    r_long = govern(node)
    assert r_long.verdict == "DELEGATED_LEGITIMATE", f"long chain: {r_long.verdict}"
    assert r_long.chain_depth == 10

    # ── Runaway delegation (depth > MAX_CHAIN_DEPTH) → treated as SELF_REFERENTIAL ──
    node2 = apex
    for i in range(_MAX_CHAIN_DEPTH + 5):
        node2 = AuthorityClaim(
            f"Runaway level {i}", LegitimacyType.RATIONAL_LEGAL,
            consent_score=0.65, verifiability=0.60, revocable=True,
            scope="sub",
            delegates_from=node2,
        )
    r_run = govern(node2)
    assert r_run.verdict == "SELF_REFERENTIAL", f"runaway: {r_run.verdict}"

    # ── Bare Grundnorm ──
    r_gn = govern(apex)
    assert r_gn.verdict == "CONSTITUTIONAL", f"grundnorm: {r_gn.verdict}"

    # ── Zero-consent root — cannot be a Grundnorm ──
    zero_consent = AuthorityClaim(
        "Zero-consent root", LegitimacyType.RATIONAL_LEGAL,
        consent_score=0.0, verifiability=0.80, revocable=True,
        scope="all",
    )
    r_zc = govern(zero_consent)
    assert r_zc.verdict == "AUTHORITY_VOID", f"zero-consent: {r_zc.verdict}"

    # ── Traditional legitimacy at root — not sufficient for Grundnorm ──
    traditional_root = AuthorityClaim(
        "Ancient custom", LegitimacyType.TRADITIONAL,
        consent_score=0.80, verifiability=0.70, revocable=False,
        scope="all",
    )
    r_trad = govern(traditional_root)
    assert r_trad.verdict == "AUTHORITY_VOID", f"traditional root: {r_trad.verdict}"

    # ── Self-derived nested in rational-legal chain (early return) ──
    sd = AuthorityClaim(
        "Self-derived claim", LegitimacyType.SELF_DERIVED,
        consent_score=0.50, verifiability=0.50, revocable=True,
        scope="approval",
        delegates_from=apex,      # has a valid parent — but SELF_DERIVED is still usurpation
    )
    r_sd = govern(sd)
    assert r_sd.verdict == "SELF_REFERENTIAL", f"self-derived: {r_sd.verdict}"

    # ── Non-revocable legitimate chain → DELEGATED_CONTESTED ──
    non_rev = AuthorityClaim(
        "Non-revocable agency", LegitimacyType.RATIONAL_LEGAL,
        consent_score=0.72, verifiability=0.70, revocable=False,
        scope="enforcement",
        delegates_from=apex,
    )
    r_nr = govern(non_rev)
    assert r_nr.verdict == "DELEGATED_CONTESTED", f"non-revocable: {r_nr.verdict}"

    print("stress-test passed (7 adversarial cases: long chain, runaway, bare Grundnorm, "
          "zero-consent root, traditional root, self-derived nested, non-revocable)")


# ─────────────────────────────────────────────────────────────────────────────
# Self-test
# ─────────────────────────────────────────────────────────────────────────────

def _self_test() -> None:
    cases   = _cases()
    rulings = audit(cases)
    verdicts = [r.verdict for r in rulings]

    expected = [
        "CONSTITUTIONAL",        # the constitution IS the Grundnorm
        "DELEGATED_LEGITIMATE",  # clean chain: constitution → parliament → agency
        "DELEGATED_CONTESTED",   # chain reaches Grundnorm but opaque_board has low scores
        "SELF_REFERENTIAL",      # AI self-cert: SELF_DERIVED type
        "SELF_REFERENTIAL",      # cycle: board_a → board_b → board_a
        "AUTHORITY_VOID",        # chain terminates at charismatic leader (not rational-legal)
    ]
    assert verdicts == expected, f"got {verdicts}"

    # CONSTITUTIONAL: chain depth = 1, grundnorm_name = itself
    r_const = rulings[0]
    assert r_const.chain_depth == 1
    assert r_const.grundnorm_name == "Constitutional Democratic Assembly"
    assert r_const.governance_response == "AFFIRM"

    # DELEGATED_LEGITIMATE: chain depth = 3, grundnorm reached
    r_del = rulings[1]
    assert r_del.chain_depth == 3
    assert r_del.grundnorm_name == "Constitutional Democratic Assembly"
    assert r_del.cycle_detected is False

    # SELF_REFERENTIAL: cycle_detected
    assert rulings[3].cycle_detected is True
    assert rulings[4].cycle_detected is True

    # AUTHORITY_VOID: grundnorm_name is None
    assert rulings[5].grundnorm_name is None
    assert rulings[5].governance_response == "VOID"

    # AFFIRM responses
    assert rulings[0].governance_response == "AFFIRM"
    assert rulings[1].governance_response == "AFFIRM"
    # VOID responses
    assert rulings[3].governance_response == "VOID"
    assert rulings[4].governance_response == "VOID"
    assert rulings[5].governance_response == "VOID"

    # Determinism (cycle-safe)
    apex = AuthorityClaim("A", LegitimacyType.RATIONAL_LEGAL,
                          consent_score=0.80, verifiability=0.80,
                          revocable=True, scope="all")
    assert govern(apex).verdict == govern(apex).verdict

    print("self-test passed (6/6 cases, constitutional, delegated, contested, "
          "self-referential, cycle, void, determinism)")

    # Run adversarial stress test
    _stress_test()


# ─────────────────────────────────────────────────────────────────────────────
# Main demo
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    _self_test()
    print()
    print("─" * 72)
    print("Throne Infrastructure — sovereign legitimacy, authority chains, usurpation detection")
    print("─" * 72)
    print()
    for r in audit(_cases()):
        print(r.render())
        print()

    print("─" * 72)
    print("Governance response table:")
    for verdict, response in _RESPONSE.items():
        print(f"  {verdict:<24} → {response}")
    print()
    print("Grundnorm criteria (the constitutional apex):")
    print("  type = RATIONAL_LEGAL")
    print(f"  consent_score  ≥ {_GRUNDNORM_CONSENT}")
    print(f"  verifiability  ≥ {_GRUNDNORM_VERIF}")
    print("  revocable      = True")
    print()
    print("Delegation quality thresholds:")
    print(f"  adequate consent: ≥ {_CONSENT_ADEQUATE}   weak link: < {_CONSENT_ADEQUATE}")
    print(f"  adequate verif:   ≥ {_VERIF_ADEQUATE}   weak link: < {_VERIF_ADEQUATE}")
    print(f"  max chain depth:  {_MAX_CHAIN_DEPTH} (beyond → SELF_REFERENTIAL)")
    print()
    print("The canonical AI usurpation:")
    print("  An AI system certifies its own safety by citing its own analysis.")
    print("  Legitimacy_type = SELF_DERIVED → SELF_REFERENTIAL → VOID immediately.")
    print("  The chain to a human constitutional anchor is the minimum requirement.")
    print()
    print("Honest scope: formal chain audit only. Does not verify whether the declared")
    print("chain matches actual power structures — that requires ground_truth_auditor.")
