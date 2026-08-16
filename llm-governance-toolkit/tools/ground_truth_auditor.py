#!/usr/bin/env python3
"""
ground_truth_auditor.py — is your "ground truth" actually independent of the proxy?

Every decoupling / drift / gaming detector in this toolkit rests on one assumption: that the
ground-truth signal you check the proxy against is *independent* of the proxy. If it isn't —
if the "truth" is secretly derived from the proxy, or shares the proxy's bias — then a clean
decoupling report is worthless: the two can't diverge because they're the same thing wearing
two hats. This tool audits that assumption and scores it, so you know whether a decoupling
alarm (or its silence) means anything.

The honest core: you cannot fully *confirm* independence without some labeled reference — a
few points where the real answer is known. That is the binding constraint of this whole
toolkit, made explicit here. What the auditor CAN always do without a reference is rule out
the worst case (a "truth" that is just a function of the proxy). With a reference it measures
the thing that matters: whether the two signals' ERRORS are correlated (shared bias) rather
than whether the signals themselves are (they should be — both track reality).

Verdicts: INDEPENDENT · SUSPECT · NOT_INDEPENDENT · UNVERIFIED (need a labeled reference).
Deterministic. numpy (+ matplotlib for the demo figure).
Run:  python ground_truth_auditor.py
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


SHADOW_RESIDUAL = 0.05     # if <5% of truth variance is unexplained by the proxy, it's a shadow
INDEP_OK = 0.60            # independence score at/above this = INDEPENDENT
INDEP_SUSPECT = 0.30       # below this = NOT_INDEPENDENT


@dataclass(frozen=True)
class Report:
    verdict: str
    score: float                 # independence score in [0,1]; higher = more independent
    reasons: Tuple[str, ...]
    caveat: str

    def render(self) -> str:
        L = [f"{self.verdict}   (independence {self.score:.2f})"]
        L += [f"    - {r}" for r in self.reasons]
        L.append(f"    » {self.caveat}")
        return "\n".join(L)


def _r2_on_proxy(proxy: np.ndarray, truth: np.ndarray) -> float:
    """Fraction of truth variance explained by a best-fit linear function of the proxy."""
    p = proxy - proxy.mean()
    t = truth - truth.mean()
    denom = (p @ p)
    if denom < 1e-12 or (t @ t) < 1e-12:
        return 0.0
    beta = (p @ t) / denom
    resid = t - beta * p
    return float(1.0 - (resid @ resid) / (t @ t))


def _corr(a: np.ndarray, b: np.ndarray) -> float:
    if a.std() < 1e-9 or b.std() < 1e-9:
        return 0.0
    return float(np.corrcoef(a, b)[0, 1])


def audit(proxy, truth, shared_source: bool = False,
          reference: Optional[np.ndarray] = None) -> Report:
    """Audit whether `truth` is an independent measurement relative to `proxy`.

    shared_source: declared — the truth is derived from, or shares data with, the proxy.
    reference:     optional labeled ground truth for a calibration window (the real answer).
    """
    proxy = np.asarray(proxy, float); truth = np.asarray(truth, float)
    reasons: List[str] = []

    if shared_source:
        return Report("NOT_INDEPENDENT", 0.0,
                      ("declared to share a data source with the proxy — it cannot be an "
                       "independent check by construction",),
                      "Get a truth signal collected independently of the proxy.")

    # worst case, detectable without a reference: truth is essentially a function of the proxy
    r2 = _r2_on_proxy(proxy, truth)
    residual = 1.0 - r2
    if residual < SHADOW_RESIDUAL:
        reasons.append(f"{r2:.2f} of the truth is explained by the proxy alone — it carries "
                       "almost no information the proxy doesn't; it is a shadow of the proxy")
        return Report("NOT_INDEPENDENT", round(max(0.0, residual), 2), tuple(reasons),
                      "A near-deterministic function of the proxy cannot detect the proxy drifting.")

    if reference is None:
        reasons.append(f"carries information beyond the proxy ({residual:.0%} of its variance is "
                       "not explained by the proxy) — necessary, but not sufficient")
        return Report("UNVERIFIED", 0.5, tuple(reasons),
                      "Independence cannot be CONFIRMED without a labeled reference. Provide a few "
                      "points where the real answer is known, and re-run.")

    # with a reference: the real test — do the two signals' ERRORS correlate (shared bias)?
    reference = np.asarray(reference, float)
    pe, te = proxy - reference, truth - reference
    ec = _corr(pe, te)
    score = max(0.0, 1.0 - max(0.0, ec))
    reasons.append(f"error-correlation with the proxy = {ec:+.2f} "
                   "(both signals err together = shared bias = not independent)")
    reasons.append(f"{residual:.0%} of truth variance is independent of the proxy")
    verdict = ("INDEPENDENT" if score >= INDEP_OK else
               "SUSPECT" if score >= INDEP_SUSPECT else "NOT_INDEPENDENT")
    caveat = ("Decoupling alarms against this truth are trustworthy." if verdict == "INDEPENDENT"
              else "Treat decoupling alarms against this truth with caution — it shares error with the proxy.")
    return Report(verdict, round(score, 2), tuple(reasons), caveat)


# ---------------------------------------------------------------------------
# Demonstrations (deterministic).
# ---------------------------------------------------------------------------
def _cases():
    rng = np.random.default_rng(7)
    n = 120
    reality = np.cumsum(rng.normal(0, 1, n)) + 50            # the real underlying signal
    # 1. genuinely independent: both track reality with INDEPENDENT noise
    proxy = reality + rng.normal(0, 2, n)
    truth_indep = reality + rng.normal(0, 2, n)
    # 2. shadow: "truth" is essentially a rescaled copy of the proxy (no reference needed to catch)
    truth_shadow = 0.85 * proxy + 3.0 + rng.normal(0, 0.3, n)
    # 3. shared bias: both track reality with independent noise AND a SHARED bias term
    #    (so they carry info beyond a copy, yet their ERRORS correlate — the real test)
    bias = rng.normal(0, 4, n)
    proxy_b = reality + bias + rng.normal(0, 2, n)
    truth_bias = reality + bias + rng.normal(0, 2, n)
    return {
        "independent (independent noise)": (proxy, truth_indep, False, reality),
        "shadow (truth = rescaled proxy)": (proxy, truth_shadow, False, None),
        "shared bias (correlated errors)": (proxy_b, truth_bias, False, reality),
        "declared shared source":          (proxy, truth_indep, True, reality),
    }


def fig(path: str) -> None:
    cases = _cases()
    names, scores, cols = [], [], []
    cmap = {"INDEPENDENT": "2E7D50", "SUSPECT": "E08A1E", "NOT_INDEPENDENT": "C0392B", "UNVERIFIED": "888888"}
    for name, (p, t, ss, ref) in cases.items():
        r = audit(p, t, shared_source=ss, reference=ref)
        names.append(f"{name}\n[{r.verdict}]"); scores.append(r.score); cols.append("#" + cmap[r.verdict])
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    ax.bar(range(len(names)), scores, color=cols)
    ax.set_xticks(range(len(names))); ax.set_xticklabels(names, fontsize=8.5)
    ax.set_ylabel("independence score"); ax.set_ylim(0, 1.05)
    ax.axhline(INDEP_OK, ls=":", c="grey")
    ax.set_title("Is your ground truth actually independent of the proxy?", fontsize=12, weight="bold")
    for i, s in enumerate(scores):
        ax.text(i, s + 0.02, f"{s:.2f}", ha="center", fontsize=9)
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)


def _self_test() -> None:
    c = _cases()
    assert audit(*c["independent (independent noise)"]).verdict == "INDEPENDENT"
    assert audit(*c["shadow (truth = rescaled proxy)"]).verdict == "NOT_INDEPENDENT"
    assert audit(*c["shared bias (correlated errors)"]).verdict in ("SUSPECT", "NOT_INDEPENDENT")
    assert audit(*c["declared shared source"]).verdict == "NOT_INDEPENDENT"
    # without a reference, an independent-looking signal is honestly UNVERIFIED, not confirmed
    p, t, _, _ = c["independent (independent noise)"]
    assert audit(p, t, reference=None).verdict == "UNVERIFIED"
    # determinism
    assert audit(*c["shared bias (correlated errors)"]).score == audit(*c["shared bias (correlated errors)"]).score
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- auditing four candidate 'ground truth' signals ---\n")
    for name, (p, t, ss, ref) in _cases().items():
        print(f"{name}:"); print(audit(p, t, shared_source=ss, reference=ref).render(), "\n")
    fig("ground_truth_auditor_fig.png")
    print("figure: ground_truth_auditor_fig.png")
