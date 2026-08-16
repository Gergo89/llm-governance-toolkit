#!/usr/bin/env python3
"""
governed_decision.py — a governed operational-decision keystone.

WHAT THIS IS
The toolkit already has the *pieces* of a high-stakes decision, but nothing that composes them
into a single, auditable decision. This does that. Given a decision to be made ("intervene on
the failing peg?", "trigger the recall?", "escalate?"), it routes that decision through the
governance components already built and returns ONE ordered outcome — with the machine able to
recommend, but structurally unable to authorize itself. A human holds the pen.

It orders DECISIONS the way soi_pipeline orders CLAIMS: by governed status, never by fiat. The
five gates, in order (each fail-closed — an unmet gate stops promotion, it does not pass):

  Gate 0  Trust the signal   -> ground_truth_auditor : is the truth signal the belief rests on
                               actually independent of the proxy? A decision built on a signal
                               that can't disagree with its proxy is not a decision. (optional:
                               only runs if proxy/truth series are supplied)
  Gate 1  Evidence floor     -> knowledge_maturity   : does the decision MODEL have any
                               evidentiary footing at all? A model at ANECDOTE maturity can't
                               carry a Bayes-optimal decision — withhold.
  Gate 2  Timing (when)      -> optimal_timing        : is acting NOW Bayes-optimal for the
                               cost structure, or is it optimal to keep monitoring? (act too
                               early = false-alarm cost; act too late = miss cost)
  Gate 3  Safety (whether)   -> containment_guard     : if we would act, is the proposed action
                               human-gated, reversible, bounded, and logged? If not, it cannot
                               be forwarded — block and escalate.
  Gate 4  Authority (who)    -> non-self-approval      : an action optimal + safe still only
                               becomes AUTHORIZED when a DISTINCT human (not the proposing
                               agent) signs. Absent that, it is a recommendation pending a human.

OUTCOME LADDER (never "ACTED" — execution is always external to this tool):
  WITHHOLD          the decision has no trustworthy/mature basis; don't decide on it yet
  GATHER_MORE       optimal to keep monitoring; below the act boundary
  BLOCK_UNSAFE      acting is optimal but the proposed action isn't containable — escalate
  RECOMMEND_ACT     optimal, safe, well-founded — PENDING a human authorization signature
  AUTHORIZED_ACT    all gates pass AND a distinct human signed — hand to the external executor

DETERMINISM
Pure function of the declared DecisionCase (optimal_timing's DP is deterministic; the audit and
maturity stages are pure). Same case -> same record and fingerprint, byte for byte.

Reuses optimal_timing, ground_truth_auditor, knowledge_maturity, containment_guard — unchanged.
Run:  python governed_decision.py
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional, Tuple
import hashlib, json, os, sys
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_PATTERNS = os.path.join(os.path.dirname(_HERE), "patterns")
for _p in (_HERE, _PATTERNS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import optimal_timing as ot            # noqa: E402
import ground_truth_auditor as gta     # noqa: E402
import knowledge_maturity as km        # noqa: E402
import containment_guard as cg         # noqa: E402
from containment_guard import ActionSpec  # noqa: E402


# Minimum evidentiary footing the decision MODEL must have before we run a decision on it.
MIN_MATURITY = km.Maturity.SUPPORTED


class Outcome(IntEnum):
    WITHHOLD = 0        # no trustworthy/mature basis to decide on
    GATHER_MORE = 1     # keep monitoring; not yet optimal to act
    BLOCK_UNSAFE = 2    # acting is optimal but the action can't be safely forwarded
    RECOMMEND_ACT = 3   # optimal + safe + founded — pending a human signature
    AUTHORIZED_ACT = 4  # all gates pass AND a distinct human authorized


@dataclass(frozen=True)
class DecisionCase:
    """A single operational decision submitted for governance.

    id, question:   identity and the one-line decision to be made.
    author:         the agent/AI proposing the decision. NOT an authority.
    posterior:      current belief in [0,1] that the acted-on condition is real.
    step:           current time step (indexes the optimal-timing DP boundary).
    model:          optimal_timing.Model — the cost structure (false-alarm vs miss, hazard, …).
    evidence:       declared evidentiary properties of the decision MODEL (-> knowledge_maturity).
    action:         the ActionSpec that would be taken if we act (-> containment_guard).
    reviewer_id:    a DISTINCT human sign-off; '' / author / 'auto' / 'system' => none.
    proxy, truth, reference:  optional signal series to audit the truth's independence (Gate 0).
    shared_source:  optional declaration that truth shares a data source with the proxy.
    """
    id: str
    question: str
    author: str
    posterior: float
    step: int
    model: ot.Model
    evidence: km.Evidence
    action: ActionSpec
    reviewer_id: str = ""
    proxy: Optional[Tuple[float, ...]] = None
    truth: Optional[Tuple[float, ...]] = None
    reference: Optional[Tuple[float, ...]] = None
    shared_source: bool = False


@dataclass(frozen=True)
class DecisionRecord:
    id: str
    question: str
    outcome: Outcome
    timing: str                 # ACT | WAIT | n/a
    act_boundary: float         # the DP act-threshold at this step (for audit)
    maturity: str
    trust: str                  # signal-independence verdict or "not audited"
    containable: Optional[bool]
    authorized_by: str          # the distinct human, or ""
    reasons: Tuple[str, ...]
    human_authority_note: str

    def to_dict(self) -> dict:
        return {"id": self.id, "question": self.question,
                "outcome": int(self.outcome), "outcome_name": self.outcome.name,
                "timing": self.timing, "act_boundary": round(self.act_boundary, 4),
                "maturity": self.maturity, "trust": self.trust,
                "containable": self.containable, "authorized_by": self.authorized_by,
                "reasons": list(self.reasons),
                "human_authority_note": self.human_authority_note}

    def render(self) -> str:
        L = [f"{self.id}: {self.question}",
             f"  OUTCOME     {self.outcome.name}",
             f"  timing      {self.timing}  (act if posterior ≥ {self.act_boundary:.2f})",
             f"  maturity    {self.maturity}",
             f"  trust       {self.trust}"]
        if self.containable is not None:
            L.append(f"  containable {self.containable}")
        for r in self.reasons:
            L.append(f"    - {r}")
        L.append(f"  » {self.human_authority_note}")
        return "\n".join(L)


def _human_signed(case: DecisionCase) -> bool:
    rid = (case.reviewer_id or "").strip()
    return bool(rid) and rid.lower() not in ("", "auto", "system") \
        and rid.strip().lower() != case.author.strip().lower()


def decide(case: DecisionCase) -> DecisionRecord:
    """Route one decision through the five gates. Deterministic, fail-closed."""
    reasons: List[str] = []
    PENDING = ("Human authority final: this is a recommendation. Nothing acts until a distinct "
               "human authorizes; the executor is external to this tool.")

    # ---- Gate 0: trust the signal the belief rests on (optional) -----------------------
    trust = "not audited"
    if case.shared_source or (case.proxy is not None and case.truth is not None):
        ref = None if case.reference is None else np.asarray(case.reference, float)
        rep = gta.audit(np.asarray(case.proxy or [], float),
                        np.asarray(case.truth or [], float),
                        shared_source=case.shared_source, reference=ref)
        trust = rep.verdict
        if rep.verdict == "NOT_INDEPENDENT":
            reasons.append(f"truth signal is NOT independent of the proxy ({rep.reasons[0]}); "
                           "a decision on it can't be trusted")
            return DecisionRecord(case.id, case.question, Outcome.WITHHOLD, "n/a", float("nan"),
                                  "not reached", trust, None, "", tuple(reasons),
                                  "Withheld: get an independent truth signal before deciding.")
        if rep.verdict in ("UNVERIFIED", "SUSPECT"):
            reasons.append(f"signal independence is {rep.verdict} — proceed, but the decision "
                           "inherits this caveat")

    # ---- Gate 1: evidentiary floor on the decision model -------------------------------
    assess = km.classify(case.evidence)
    maturity = assess.level.name
    if assess.level < MIN_MATURITY:
        reasons.append(f"decision model maturity is {maturity} (< {MIN_MATURITY.name}); "
                       "too weak an evidentiary footing to run a decision on")
        return DecisionRecord(case.id, case.question, Outcome.WITHHOLD, "n/a", float("nan"),
                              maturity, trust, None, "", tuple(reasons),
                              "Withheld: strengthen the evidence base before deciding.")

    # ---- Gate 2: timing — is acting now optimal? ---------------------------------------
    sol = ot.solve(case.model)
    step = max(0, min(case.step, len(sol["boundary"]) - 1))
    boundary = float(sol["boundary"][step])
    timing = ot.decide(case.step, case.posterior, sol)
    if timing == "WAIT":
        reasons.append(f"posterior {case.posterior:.2f} is below the optimal act-threshold "
                       f"{boundary:.2f} at step {step} — optimal to keep monitoring")
        return DecisionRecord(case.id, case.question, Outcome.GATHER_MORE, timing, boundary,
                              maturity, trust, None, "", tuple(reasons),
                              "No action recommended yet; revisit as evidence arrives.")
    reasons.append(f"posterior {case.posterior:.2f} ≥ act-threshold {boundary:.2f} at step "
                   f"{step} — acting now is Bayes-optimal for the cost structure")

    # ---- Gate 3: safety — is the proposed action containable? --------------------------
    try:
        cg.check(case.action)
        containable = True
    except cg.ContainmentViolation as e:
        reasons.append(f"acting is optimal, but the proposed action is not containable: {e}")
        return DecisionRecord(case.id, case.question, Outcome.BLOCK_UNSAFE, timing, boundary,
                              maturity, trust, False, "", tuple(reasons),
                              "Blocked: the action cannot be forwarded as-is. Escalate / redesign "
                              "the action to be reversible, bounded, and logged.")

    # ---- Gate 4: authority — non-self-approval -----------------------------------------
    if _human_signed(case):
        reasons.append(f"distinct human authority '{case.reviewer_id}' has authorized the action")
        return DecisionRecord(case.id, case.question, Outcome.AUTHORIZED_ACT, timing, boundary,
                              maturity, trust, containable, case.reviewer_id.strip(),
                              tuple(reasons),
                              "Authorized by a named human. Hand to the external executor for one "
                              "reversible, logged action.")
    reasons.append("no distinct human has signed — the machine cannot authorize its own action")
    return DecisionRecord(case.id, case.question, Outcome.RECOMMEND_ACT, timing, boundary,
                          maturity, trust, containable, "", tuple(reasons), PENDING)


def fingerprint(rec: DecisionRecord) -> str:
    return hashlib.sha256(json.dumps(rec.to_dict(), sort_keys=True).encode()).hexdigest()


# ---------------------------------------------------------------------------
# Demonstrations.
# ---------------------------------------------------------------------------
def _good_action(desc="throttle the mechanism to 5% and monitor"):
    return ActionSpec(desc, requires_human_ok=True, reversible=True, scope="minimal",
                      rollback_plan="restore prior setting; effect reverts within one interval",
                      logged=True)


def _mature():
    return km.Evidence(observation_count=12, distinct_methods=2,
                       independently_replicated=True, adversarially_tested=True)


def _shadow_series(n=120, seed=7):
    rng = np.random.default_rng(seed)
    reality = np.cumsum(rng.normal(0, 1, n)) + 50
    proxy = reality + rng.normal(0, 2, n)
    truth = 0.85 * proxy + 3.0 + rng.normal(0, 0.3, n)     # a shadow of the proxy
    return tuple(proxy), tuple(truth)


def _cases():
    m = ot.Model()                                          # miss 5x a false alarm
    authorized = DecisionCase(
        "DEC-1", "Intervene now on the destabilizing peg?", author="agent-monitor",
        posterior=0.92, step=2, model=m, evidence=_mature(),
        action=_good_action(), reviewer_id="human:risk-officer")
    pending = DecisionCase(
        "DEC-2", "Intervene now on the destabilizing peg?", author="agent-monitor",
        posterior=0.92, step=2, model=m, evidence=_mature(),
        action=_good_action(), reviewer_id="")             # no human signature yet
    wait = DecisionCase(
        "DEC-3", "Intervene now on the destabilizing peg?", author="agent-monitor",
        posterior=0.20, step=2, model=m, evidence=_mature(),
        action=_good_action(), reviewer_id="human:risk-officer")
    unsafe = DecisionCase(
        "DEC-4", "Hard-shutdown the exchange irreversibly?", author="agent-monitor",
        posterior=0.92, step=2, model=m, evidence=_mature(),
        action=ActionSpec("wipe the order book (irreversible)", requires_human_ok=True,
                          reversible=False, scope="broad", rollback_plan=None, logged=True),
        reviewer_id="human:risk-officer")
    thin = DecisionCase(
        "DEC-5", "Intervene now on the destabilizing peg?", author="agent-monitor",
        posterior=0.92, step=2, model=m,
        evidence=km.Evidence(observation_count=1),          # anecdote — no footing
        action=_good_action(), reviewer_id="human:risk-officer")
    px, tr = _shadow_series()
    untrusted = DecisionCase(
        "DEC-6", "Intervene based on this health signal?", author="agent-monitor",
        posterior=0.92, step=2, model=m, evidence=_mature(),
        action=_good_action(), reviewer_id="human:risk-officer",
        proxy=px, truth=tr)                                 # truth is a shadow of the proxy
    return {"optimal + safe + human-signed": authorized,
            "optimal + safe, no signature": pending,
            "below act-threshold": wait,
            "optimal but unsafe action": unsafe,
            "evidence too thin": thin,
            "untrustworthy truth signal": untrusted}


def _self_test() -> None:
    c = _cases()
    assert decide(c["optimal + safe + human-signed"]).outcome == Outcome.AUTHORIZED_ACT
    assert decide(c["optimal + safe, no signature"]).outcome == Outcome.RECOMMEND_ACT
    assert decide(c["below act-threshold"]).outcome == Outcome.GATHER_MORE
    assert decide(c["optimal but unsafe action"]).outcome == Outcome.BLOCK_UNSAFE
    assert decide(c["evidence too thin"]).outcome == Outcome.WITHHOLD
    assert decide(c["untrustworthy truth signal"]).outcome == Outcome.WITHHOLD

    # the machine cannot authorize its own action: signing as the author does not count
    self_signed = DecisionCase(
        "DEC-S", "self-authorize?", author="agent-monitor", posterior=0.92, step=2,
        model=ot.Model(), evidence=_mature(), action=_good_action(),
        reviewer_id="agent-monitor")
    assert decide(self_signed).outcome == Outcome.RECOMMEND_ACT

    # determinism: same case -> identical fingerprint
    a = decide(c["optimal + safe + human-signed"])
    b = decide(c["optimal + safe + human-signed"])
    assert fingerprint(a) == fingerprint(b)
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- governed operational decisions (recommends; never self-authorizes) ---\n")
    for name, case in _cases().items():
        print(f"# {name}")
        rec = decide(case)
        print(rec.render())
        print(f"  fingerprint {fingerprint(rec)[:16]} …\n")
