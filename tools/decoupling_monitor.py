#!/usr/bin/env python3
"""
decoupling_monitor.py — catch Goodhart gaming in the wild, as it emerges.

The goodhart_auditor catches a metric that *overclaims by name* at definition time.
This tool catches the other half: a metric that was honest but is being *gamed in
operation* — the reported proxy keeps improving while the ground truth it was supposed
to represent stagnates or degrades. That divergence is the operational signature of
Goodhart's law, and it is exactly the pattern behind the money model's peg drifting
from its backing, and behind "same price, worse product" hidden inflation.

Give it two aligned time series — a `proxy` (the optimized/reported metric) and an
independent `truth` (a ground-truth measure of what the proxy should track). It reports,
per step, whether they are TRACKING, DRIFTING, or DECOUPLED, and raises an alert when
the proxy is rising while the truth is falling and their co-movement has broken — ideally
*before* the truth crosses a visible failure line.

What it needs, and its limit: it requires an independent ground-truth signal. If you only
have the proxy, there is nothing to check it against — which is itself the honest lesson:
you cannot detect operational gaming without a second, un-gamed measurement.

Deterministic. numpy (+ matplotlib for the demo figure).
Run:  python decoupling_monitor.py     # self-test + three demos + figure
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


@dataclass(frozen=True)
class Config:
    window: int = 8          # rolling window for co-movement and trend
    corr_break: float = 0.3  # co-movement below this counts as "broken"
    gap_warn: float = 2.5    # proxy-minus-truth (indexed pts) that counts as drift
    sustain: int = 2         # consecutive flagged steps before an alert fires
    fail_level: float = 92.0 # truth index level counted as a visible failure (100 = start)


def _index(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    base = x[0] if x[0] != 0 else 1.0
    return 100.0 * x / base


def _roll_corr(a: np.ndarray, b: np.ndarray, w: int) -> np.ndarray:
    """Rolling correlation of the STEP CHANGES of a and b."""
    da, db = np.diff(a, prepend=a[0]), np.diff(b, prepend=b[0])
    n = len(a); out = np.zeros(n)
    for t in range(n):
        lo = max(0, t - w + 1)
        xa, xb = da[lo:t + 1], db[lo:t + 1]
        if len(xa) < 3 or xa.std() < 1e-9 or xb.std() < 1e-9:
            out[t] = 1.0
        else:
            out[t] = float(np.corrcoef(xa, xb)[0, 1])
    return out


def _trend(x: np.ndarray, w: int) -> np.ndarray:
    n = len(x); out = np.zeros(n)
    for t in range(n):
        lo = max(0, t - w + 1)
        seg = x[lo:t + 1]
        out[t] = seg[-1] - seg[0]
    return out


def monitor(proxy, truth, cfg: Config = Config()) -> Dict[str, object]:
    """Classify tracking vs decoupling over time and return the alert step (if any)."""
    p, u = _index(proxy), _index(truth)
    corr = _roll_corr(p, u, cfg.window)
    gap = p - u
    ptr, utr = _trend(p, cfg.window), _trend(u, cfg.window)

    # per-step flag: co-movement broken AND proxy rising while truth falling AND gap opened
    flag = (corr < cfg.corr_break) & (ptr > 0) & (utr < 0) & (gap > cfg.gap_warn)
    status = np.where(flag, "DECOUPLED",
             np.where((gap > cfg.gap_warn) | (corr < cfg.corr_break), "DRIFTING", "TRACKING"))

    # alert = first run of `sustain` consecutive DECOUPLED steps
    alert: Optional[int] = None
    run = 0
    for t in range(len(flag)):
        run = run + 1 if flag[t] else 0
        if run >= cfg.sustain:
            alert = t - cfg.sustain + 1
            break

    fail_idx = np.where(u < cfg.fail_level)[0]
    truth_fail = int(fail_idx[0]) if len(fail_idx) else None
    lead = (truth_fail - alert) if (alert is not None and truth_fail is not None) else None

    return {"proxy_idx": p, "truth_idx": u, "corr": corr, "gap": gap,
            "status": status, "alert": alert, "truth_fail": truth_fail, "lead": lead}


# ---------------------------------------------------------------------------
# Demonstration series (deterministic).
# ---------------------------------------------------------------------------
def _series(kind: str, n: int = 60, seed: int = 4):
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    if kind == "honest":            # both genuinely improve together
        base = 100 + 0.6 * t
        return base + rng.normal(0, 1.2, n), base + rng.normal(0, 1.2, n)
    if kind == "gamed":             # proxy keeps climbing; truth quietly degrades after t0
        t0 = 20
        proxy = 100 + 0.7 * t + rng.normal(0, 0.8, n)
        truth = 100 + 0.7 * t + rng.normal(0, 0.8, n)
        truth[t0:] = truth[t0] - 0.9 * (t[t0:] - t0) + rng.normal(0, 0.8, n - t0)
        return proxy, truth
    # noisy-but-honest: flat, correlated noise, no real divergence
    common = rng.normal(0, 1.5, n)
    return 100 + common + rng.normal(0, 0.6, n), 100 + common + rng.normal(0, 0.6, n)


def fig_demo(path: str) -> None:
    fig, ax = plt.subplots(1, 3, figsize=(13.5, 4.2))
    fig.suptitle("Decoupling monitor: proxy vs ground truth — gaming shows as divergence",
                 fontsize=12, weight="bold")
    for j, kind in enumerate(("honest", "gamed", "noisy")):
        p, u = _series(kind)
        res = monitor(p, u)
        ax[j].plot(res["proxy_idx"], color="crimson", label="proxy (reported)")
        ax[j].plot(res["truth_idx"], color="seagreen", label="truth (independent)")
        ax[j].axhline(Config().fail_level, ls=":", c="grey", lw=0.8)
        if res["alert"] is not None:
            ax[j].axvline(res["alert"], ls="--", c="black",
                          label=f"ALERT @ {res['alert']}" +
                          (f" (lead {res['lead']})" if res["lead"] is not None else ""))
        title = {"honest": "Honest: both improve", "gamed": "Gamed: proxy up, truth down",
                 "noisy": "Noisy but honest"}[kind]
        verdict = "alert" if res["alert"] is not None else "no alert"
        ax[j].set_title(f"{title}  →  {verdict}", fontsize=10)
        ax[j].set_xlabel("time"); ax[j].legend(fontsize=7)
    ax[0].set_ylabel("indexed level (start = 100)")
    fig.tight_layout(rect=(0, 0, 1, 0.93)); fig.savefig(path, dpi=120); plt.close(fig)


def _self_test() -> None:
    # Gamed series must raise an alert, and before the truth visibly fails.
    g = monitor(*_series("gamed"))
    assert g["alert"] is not None
    assert g["truth_fail"] is not None and g["lead"] is not None and g["lead"] >= 0

    # Honest (both up) and noisy-but-honest must NOT raise an alert.
    assert monitor(*_series("honest"))["alert"] is None
    assert monitor(*_series("noisy"))["alert"] is None

    # Determinism.
    assert monitor(*_series("gamed"))["alert"] == monitor(*_series("gamed"))["alert"]
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    print("\n--- decoupling monitor on three regimes ---")
    for kind in ("honest", "gamed", "noisy"):
        r = monitor(*_series(kind))
        a = r["alert"]
        line = (f"ALERT at t={a}" + (f", {r['lead']} steps before truth failed" if r["lead"] is not None else "")
                if a is not None else "no alert (tracking)")
        print(f"  {kind:8} -> {line}")
    fig_demo("decoupling_monitor_fig.png")
    print("\nfigure: decoupling_monitor_fig.png")
