#!/usr/bin/env python3
"""
gene_shift_infra.py — antigenic drift-then-shift as a proxy/truth decoupling worked example.

Biology primer (brief).  Influenza surface proteins mutate in two distinct ways:

  DRIFT  — continuous, gradual amino-acid substitution in HA/NA antigens.  Each new season's
            circulating strain is slightly further from the reference vaccine strain.  Immune
            recognition erodes slowly but measurably.

  SHIFT  — abrupt gene-segment reassortment when two strains co-infect the same cell.
            A novel HA/NA subtype combination appears suddenly (H1N1 → H2N2, or H3N2 → H1N1,
            etc.).  Prior immunity is largely irrelevant to the new subtype: immune escape is
            discontinuous, pandemic-scale.

Both are proxy/truth decoupling:

  Drift = slow Goodhart.  The vaccine-matched antibody titer (proxy) stays high while actual
          cross-reactive immunity against the circulating strain (truth) quietly degrades.
          Measurable.  Preventable if detected early.

  Shift = abrupt Goodhart.  The reference-strain assay (proxy) is now measuring the wrong
          antigen entirely.  One gene-segment swap invalidates the proxy almost completely;
          the gap widens discontinuously rather than gradually.

`decoupling_monitor` catches both: drift as a gradual correlation break that fires an alert
with significant lead time before the truth crosses a visible failure threshold, and shift as
a sudden gap spike that registers on the same tool — no separate detector needed.

Frameshift analogy (see tokenization_taxonomy.py).  A ±1 insertion/deletion in an RNA sequence
shifts all downstream codon boundaries, corrupting every downstream amino-acid.  A genomic
reassortment is a segment-level version of the same thing: upstream segmentation (which gene
segments co-habit a virion) is a lossy prior that determines all downstream interpretation.
Both are cases where a single upstream boundary error cascades to every downstream token.

Scope note.  The time series below are a stylized, deterministic model for demonstrating the
monitoring discipline.  They are NOT an epidemiological simulation.  Real antigenic distances,
HI-titer values, and immune-failure thresholds vary by pathogen, season, and cohort.  What is
real: the naming (drift/shift), the asymmetry (drift = gradual, shift = abrupt), and the claim
that lab-assay proxies decouple from actual immune protection in exactly these two ways — a fact
documented in influenza surveillance literature (e.g. Koel et al. 2013; Bedford et al. 2014).

Deterministic (seeded).  Requires numpy and matplotlib.
Run:  python gene_shift_infra.py
"""

from __future__ import annotations
import os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

import decoupling_monitor as dm


# ---------------------------------------------------------------------------
# Config tuned for the two-phase immune scenario
# ---------------------------------------------------------------------------
GENE_CFG = dm.Config(
    window=8,
    corr_break=0.20,   # tight: proxy rising while truth falls = immediate anti-correlation
    gap_warn=4.0,      # indexed pts; gap opens at ~0.7/step, crosses this at t≈6
    sustain=2,
    fail_level=85.0,   # truth index < 85 = clinically meaningful immune insufficiency
)


# ---------------------------------------------------------------------------
# Time-series generator
# ---------------------------------------------------------------------------
def drift_then_shift_series(
    n: int = 60,
    shift_t: int = 40,
    seed: int = 42,
):
    """
    Two-phase immune time series.

    proxy — HI (hemagglutination inhibition) titer against the REFERENCE strain.
             The lab keeps measuring against the freeze-stocked vaccine strain, which doesn't
             change.  During drift it stays high (mild seasonal booster effect) or rises
             slightly.  After shift it remains high: the lab is measuring the wrong antigen.

    truth — actual cross-reactive neutralization titer against the CIRCULATING strain.
             Drifts down as the circulating strain mutates away from the reference over
             ~3 years, then drops abruptly at the shift event as a novel HA/NA subtype
             renders prior antibodies largely non-neutralising.

    Returns (proxy: ndarray, truth: ndarray), both starting at ≈100.
    """
    rng = np.random.default_rng(seed)
    t = np.arange(n)

    proxy = np.zeros(n)
    truth = np.zeros(n)

    # Drift phase (t = 0 .. shift_t-1)
    # Proxy: reference-strain titer holds steady with mild seasonal boost.
    # Truth: circulating-strain cross-reactivity decays as the virus mutates.
    proxy[:shift_t] = 100 + 0.15 * t[:shift_t] + rng.normal(0, 0.5, shift_t)
    truth[:shift_t] = 100 - 0.55 * t[:shift_t] + rng.normal(0, 0.5, shift_t)

    # Shift event at t = shift_t
    # Gene-segment reassortment produces a novel HA/NA subtype.
    # truth drops ~20 indexed points (sudden immune escape, no cross-reactive coverage).
    # proxy barely moves (same old assay run against same old reference strain).
    post_n = n - shift_t
    shift_drop = -20.0 + rng.normal(0, 1.0)          # abrupt collapse in immune protection

    proxy[shift_t:] = (
        proxy[shift_t - 1]
        - 0.15 * np.arange(1, post_n + 1)            # slow proxy adjustment as labs update
        + rng.normal(0, 0.5, post_n)
    )
    truth[shift_t:] = (
        truth[shift_t - 1] + shift_drop              # sudden jump at shift event
        - 0.70 * np.arange(1, post_n + 1)            # continues steep decline post-shift
        + rng.normal(0, 0.5, post_n)
    )

    return proxy, truth


# ---------------------------------------------------------------------------
# Run monitor
# ---------------------------------------------------------------------------
def analyse(n: int = 60, shift_t: int = 40, seed: int = 42):
    proxy, truth = drift_then_shift_series(n, shift_t, seed)
    result = dm.monitor(proxy, truth, cfg=GENE_CFG)
    return proxy, truth, result


# ---------------------------------------------------------------------------
# Figure
# ---------------------------------------------------------------------------
def fig_gene_shift(proxy, truth, result, path: str, shift_t: int = 40):
    """
    Two-panel figure.
    Panel 1: proxy vs truth indexed series with colour-coded verdict bands,
             shift-event line, alert line, immune-failure line.
    Panel 2: rolling correlation and gap, with threshold reference lines.
    """
    p, u = result["proxy_idx"], result["truth_idx"]
    corr, gap = result["corr"], result["gap"]
    alert, tf = result["alert"], result["truth_fail"]
    lead = result["lead"]
    n = len(p)
    t = np.arange(n)
    status = result["status"]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7.5), sharex=True)
    fig.suptitle(
        "Antigenic drift  →  shift: immune proxy vs actual cross-reactive coverage\n"
        "decoupling_monitor catches both failure modes — with lead time during drift",
        fontsize=11, weight="bold",
    )

    # --- Panel 1 -----------------------------------------------------------
    # colour bands per verdict
    band = {"TRACKING": "#d4edda", "DRIFTING": "#fff3cd", "DECOUPLED": "#f8d7da"}
    for i in range(n):
        ax1.axvspan(i - 0.5, i + 0.5, color=band.get(status[i], "#ffffff"),
                    alpha=0.35, linewidth=0)

    ax1.plot(t, p, color="crimson", lw=1.8,
             label="proxy  — lab HI titer vs reference strain")
    ax1.plot(t, u, color="seagreen", lw=1.8,
             label="truth  — cross-reactive coverage vs circulating strain")
    ax1.axhline(GENE_CFG.fail_level, ls=":", c="dimgray", lw=1.0,
                label=f"immune-failure threshold ({GENE_CFG.fail_level:.0f})")
    ax1.axvline(shift_t, ls="-", c="navy", lw=1.5, alpha=0.6,
                label=f"SHIFT event (t={shift_t})  — gene-segment reassortment")

    if alert is not None:
        lead_str = f"{lead} steps before immune failure" if lead else ""
        ax1.axvline(alert, ls="--", c="black", lw=1.6,
                    label=f"ALERT  t={alert}  ({lead_str})")
    if tf is not None:
        ax1.axvline(tf, ls="--", c="darkorange", lw=1.4,
                    label=f"immune failure  t={tf}")

    # phase labels
    ax1.text(shift_t / 2, 56, "DRIFT PHASE\n(gradual mutation)", ha="center",
             va="bottom", fontsize=8, color="saddlebrown", style="italic")
    ax1.text((shift_t + n) / 2, 56, "POST-SHIFT PHASE\n(novel subtype)", ha="center",
             va="bottom", fontsize=8, color="navy", style="italic")

    ax1.set_ylabel("indexed level  (t=0 → 100)", fontsize=9)
    ax1.legend(fontsize=7, loc="upper right", framealpha=0.85)

    # --- Panel 2 -----------------------------------------------------------
    ax2.plot(t, corr, color="steelblue", lw=1.6,
             label="rolling correlation  (proxy Δ vs truth Δ)")
    ax2.axhline(GENE_CFG.corr_break, ls=":", c="steelblue", lw=0.9, alpha=0.7,
                label=f"corr_break ({GENE_CFG.corr_break})")
    ax2.axhline(0, ls="-", c="lightgray", lw=0.6)

    ax2r = ax2.twinx()
    ax2r.plot(t, gap, color="tomato", lw=1.6, ls="-.",
              label="gap = proxy_idx − truth_idx")
    ax2r.axhline(GENE_CFG.gap_warn, ls=":", c="tomato", lw=0.9, alpha=0.7,
                 label=f"gap_warn ({GENE_CFG.gap_warn})")
    ax2r.set_ylabel("gap  (indexed pts)", color="tomato", fontsize=9)

    ax2.axvline(shift_t, ls="-", c="navy", lw=1.5, alpha=0.6)
    if alert is not None:
        ax2.axvline(alert, ls="--", c="black", lw=1.6)

    ax2.set_xlabel("time step  (1 step ≈ 1 month)", fontsize=9)
    ax2.set_ylabel("rolling correlation", fontsize=9)
    ax2.legend(fontsize=7, loc="upper left", framealpha=0.85)
    ax2r.legend(fontsize=7, loc="lower right", framealpha=0.85)

    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
def _self_test():
    proxy, truth, r = analyse()

    # 1. Alert must fire — the drift decouples early.
    assert r["alert"] is not None, "expected an alert; none fired"

    # 2. Alert fires during the drift phase (before the shift event at t=40).
    assert r["alert"] < 40, f"alert fired too late: t={r['alert']}, expected during drift"

    # 3. Alert precedes immune failure (positive lead time).
    assert r["truth_fail"] is not None, (
        "truth never crossed fail_level — adjust the series or lower fail_level"
    )
    assert r["lead"] is not None and r["lead"] > 0, (
        f"expected positive lead time, got {r['lead']}"
    )

    # 4. The shift event widens the gap discontinuously beyond the drift peak.
    shift_gap = r["gap"][40]
    drift_peak = r["gap"][:40].max()
    assert shift_gap > drift_peak, (
        f"shift gap ({shift_gap:.1f}) should exceed drift peak ({drift_peak:.1f})"
    )

    # 5. After the shift the truth drops below the proxy by a large margin.
    assert r["truth_idx"][40] < r["proxy_idx"][40] - 30, (
        "expected proxy–truth gap > 30 pts immediately after shift"
    )

    # 6. Determinism.
    _, _, r2 = analyse()
    assert list(r["status"]) == list(r2["status"])
    assert r["alert"] == r2["alert"]
    assert r["truth_fail"] == r2["truth_fail"]

    print("self-test passed")


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    _self_test()

    proxy, truth, r = analyse()
    alert, tf, lead = r["alert"], r["truth_fail"], r["lead"]
    status = r["status"]

    print("\n=== Antigenic drift → shift: proxy/truth decoupling via decoupling_monitor ===\n")
    print("  PROXY  = HI titer against the reference (vaccine) strain")
    print("           — what the lab can measure without access to current circulating virus")
    print("  TRUTH  = actual cross-reactive neutralization against the circulating strain")
    print("           — what actually determines whether the host is protected")
    print()
    print(f"  Drift phase  t = 0–39  gradual mutation, vaccine proxy slowly goes stale")
    print(f"  Shift event  t = 40    gene-segment reassortment → novel HA/NA subtype")
    print()

    # Per-verdict step summary
    counts = {"TRACKING": 0, "DRIFTING": 0, "DECOUPLED": 0}
    first_last = {}
    for i, s in enumerate(status):
        v = str(s)
        counts[v] = counts.get(v, 0) + 1
        if v not in first_last:
            first_last[v] = [i, i]
        else:
            first_last[v][1] = i

    for v in ("TRACKING", "DRIFTING", "DECOUPLED"):
        c = counts.get(v, 0)
        if c:
            fl = first_last[v]
            print(f"  {v:11}  {c:3} steps  (first t={fl[0]}, last t={fl[1]})")

    print()
    if alert is not None:
        lead_str = f"{lead} steps before immune failure" if lead and lead > 0 else "simultaneous with failure"
        print(f"  ALERT fired        t = {alert}  →  {lead_str}")
        print(f"  Immune failure     t = {tf}  (truth_idx < {GENE_CFG.fail_level})")
        print(f"  Lead time          {lead} steps")
    else:
        print("  No alert — decoupling not detected (unexpected).")

    print()
    print(f"  Gap at shift event (t=40)    : {r['gap'][40]:.1f} indexed pts")
    print(f"  Peak gap during drift (t<40) : {r['gap'][:40].max():.1f} indexed pts")
    print(f"  Ratio (shift / drift peak)   : {r['gap'][40] / r['gap'][:40].max():.2f}×")
    print()
    print("  The drift alert fires with lead time — surveillance gets a window to act")
    print("  before the high proxy reading masks the underlying immune erosion.")
    print()
    print("  The shift then widens the gap discontinuously: same monitor, same tool,")
    print("  abrupt signal. No separate 'pandemic detector' needed; the logic is unified.")
    print()
    print("  Frameshift analogy: a gene-segment reassortment is upstream segmentation error")
    print("  that corrupts every downstream codon boundary — the same cascading-tokenization")
    print("  failure documented in tokenization_taxonomy.py, at the genomic scale.")

    fig_path = os.path.join(_HERE, "gene_shift_fig.png")
    fig_gene_shift(proxy, truth, r, fig_path)
    print(f"\n  figure: {fig_path}")
