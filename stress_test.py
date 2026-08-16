#!/usr/bin/env python3
"""
stress_test.py — an empirical validation battery for the governance toolkit.

Five phases, all deterministic (fixed seeds; no wall-clock in the logic):
  1. Self-test sweep       — run every module's own _self_test() as a subprocess (exit 0 = pass).
  2. Determinism           — run each module's demo 3x; stdout must be byte-identical every time.
  3. Property/invariant     — hammer each tool's mathematical invariant with many randomized,
                              seeded inputs and measure how often it holds / detects correctly.
  4. Edge cases             — degenerate inputs (empty, length-1, extreme); must not crash.
  5. Performance            — throughput (ops/sec) and mean latency on hot paths.

Honest framing (the toolkit's own standard applies to its own test): a green battery is
"not refuted across the exercised inputs," never "proven correct for all inputs."
Run:  python stress_test.py     # prints a report and writes stress_results.json
"""
from __future__ import annotations
import glob, json, os, subprocess, sys, time
from math import log

ROOT = os.path.dirname(os.path.abspath(__file__))
SUBDIRS = ["tools", "patterns", "soi", "agent_cage", "ontology_mapping"]

# Packaged subprojects: importable packages with their own test runners, not
# standalone self-testing modules. Phase 1 executes each file directly, which a
# src-layout package with relative imports cannot survive. These are excluded
# here and covered by their own CI workflow instead.
EXCLUDE_DIRS = ["compliance-toolkit"]
for d in SUBDIRS:
    sys.path.insert(0, os.path.join(ROOT, d))
import numpy as np

RESULTS: dict = {}


def _hdr(t): print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


# ---------------------------------------------------------------------------
# Phase 1 — self-test sweep (subprocess; exit 0 == pass)
# ---------------------------------------------------------------------------
def phase1_selftests():
    _hdr("PHASE 1 — self-test sweep (every module runs its own _self_test)")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(os.path.join(ROOT, d) for d in SUBDIRS)
    env["MPLBACKEND"] = "Agg"
    def _excluded(path):
        rel = os.path.relpath(path, ROOT)
        head = rel.replace(os.sep, "/").split("/")[0]
        return head in EXCLUDE_DIRS

    mods = sorted(p for p in glob.glob(os.path.join(ROOT, "**", "*.py"), recursive=True)
                  if os.path.basename(p) != "stress_test.py" and not _excluded(p))
    rows, npass, ntimed = [], 0, 0
    for p in mods:
        rel = os.path.relpath(p, ROOT)
        t0 = time.perf_counter()
        try:
            r = subprocess.run([sys.executable, p], cwd=ROOT, env=env,
                               capture_output=True, text=True, timeout=180)
            dt = time.perf_counter() - t0
            ok = (r.returncode == 0)
            asserted = "self-test passed" in r.stdout
            rows.append((rel, ok, asserted, round(dt, 3),
                         (r.stderr.strip().splitlines()[-1] if not ok and r.stderr.strip() else "")))
            npass += ok
        except subprocess.TimeoutExpired:
            rows.append((rel, False, False, 180.0, "TIMEOUT"))
    for rel, ok, asserted, dt, err in rows:
        flag = "PASS" if ok else "FAIL"
        note = "  (asserts self-test passed)" if asserted else ("  " + err if err else "")
        print(f"  [{flag}] {rel:<48} {dt:>7.2f}s{note}")
    print(f"\n  {npass}/{len(rows)} modules exited 0; "
          f"{sum(1 for _,_,a,_,_ in rows if a)}/{len(rows)} printed 'self-test passed'.")
    RESULTS["phase1_selftests"] = {"total": len(rows), "passed": npass,
                                   "asserted": sum(1 for _,_,a,_,_ in rows if a),
                                   "modules": [{"module": rel, "pass": ok, "asserted": a, "secs": dt}
                                               for rel, ok, a, dt, _ in rows]}
    return [rel for rel, ok, *_ in rows if ok]


# ---------------------------------------------------------------------------
# Phase 2 — determinism (3 runs, byte-identical stdout)
# ---------------------------------------------------------------------------
def phase2_determinism(passed_rel):
    _hdr("PHASE 2 — determinism (each demo run 3x; stdout must be byte-identical)")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(os.path.join(ROOT, d) for d in SUBDIRS)
    env["MPLBACKEND"] = "Agg"
    # exclude modules whose demo intentionally prints timing/paths; test the pure-logic ones
    skip = {"stress_test.py"}
    det_ok, det_tot, rows = 0, 0, []
    for rel in passed_rel:
        if os.path.basename(rel) in skip:
            continue
        outs = set()
        try:
            for _ in range(3):
                r = subprocess.run([sys.executable, os.path.join(ROOT, rel)], cwd=ROOT, env=env,
                                   capture_output=True, text=True, timeout=180)
                outs.add(r.stdout)
            det_tot += 1
            ok = len(outs) == 1
            det_ok += ok
            rows.append((rel, ok, len(outs)))
        except subprocess.TimeoutExpired:
            rows.append((rel, False, -1))
    nondet = [(rel, u) for rel, ok, u in rows if not ok]
    for rel, u in nondet:
        print(f"  [NON-DET] {rel}  ({u} distinct outputs over 3 runs)")
    print(f"  {det_ok}/{det_tot} modules produced byte-identical output across 3 runs.")
    if not nondet:
        print("  (every module tested is fully deterministic)")
    RESULTS["phase2_determinism"] = {"total": det_tot, "deterministic": det_ok,
                                     "nondeterministic": [rel for rel, _ in nondet]}


# ---------------------------------------------------------------------------
# Phase 3 — property / invariant tests (randomized, seeded)
# ---------------------------------------------------------------------------
def phase3_properties():
    _hdr("PHASE 3 — property/invariant tests (randomized, seeded)")
    P = {}

    # --- EM: log-likelihood monotonicity theorem, over many datasets ---------
    import em_estimation as em
    mono_ok = mono_tot = 0
    rec = unid = 0
    for seed in range(80):
        for mu in [(-5.0, 5.0), (-0.3, 0.3)]:
            x = em._mixture(seed, mu)
            r = em.fit_em(x, seed=seed)
            h = np.array(r.ll_history)
            mono_tot += 1
            if len(h) < 2 or float(np.min(np.diff(h))) >= -1e-6:
                mono_ok += 1
        rec += (em.govern("s", em._mixture(seed, (-5.0, 5.0))).verdict == "LATENT_RECOVERED")
        unid += (em.govern("o", em._mixture(seed, (-0.3, 0.3))).verdict == "UNIDENTIFIED")
    P["em_loglik_monotonic"] = {"held": mono_ok, "trials": mono_tot, "rate": mono_ok / mono_tot}
    P["em_separated_recovered"] = {"held": rec, "trials": 80, "rate": rec / 80}
    P["em_overlapping_withheld"] = {"held": unid, "trials": 80, "rate": unid / 80}
    print(f"  EM  log-likelihood monotonic (theorem): {mono_ok}/{mono_tot}")
    print(f"  EM  well-separated → LATENT_RECOVERED : {rec}/80")
    print(f"  EM  overlapping   → UNIDENTIFIED      : {unid}/80")

    # --- fractals: closed-form dimension + box-count recovery -----------------
    import fractal_recursion as fr
    closed = {"Cantor dust": log(2)/log(3), "Koch curve": log(4)/log(3),
              "Sierpinski triangle": log(3)/log(2), "Sierpinski carpet": log(8)/log(3),
              "Menger sponge": log(20)/log(3)}
    max_dim_err = max(abs(fr.similarity_dimension(s) - closed[s.name])
                      for s in fr.catalogue() if s.name in closed)
    box_errs = []
    for depth in range(6, 12):
        pts = fr.ifs_points_1d(fr._cantor_maps(), depth=depth)
        d_est = fr.box_dimension(pts, (1/3)**2, (1/3)**min(depth, 6))
        box_errs.append(abs(d_est - log(2)/log(3)))
    P["fractal_dim_closed_form_max_err"] = max_dim_err
    P["fractal_boxcount_max_err"] = max(box_errs)
    print(f"  FRACTAL  |similarity dim − closed form| max err : {max_dim_err:.2e}")
    print(f"  FRACTAL  box-count vs closed-form max err       : {max(box_errs):.2e}")

    # --- energy: conservation kept; over-unity always refused -----------------
    import energy_matter as en
    rng = np.random.default_rng(0)
    cons_ok = ou_ok = N = 0
    for _ in range(3000):
        a = float(rng.uniform(100, 1000)); N += 1
        cons_ok += (en.govern(en.EnergyLedger("c", {"in": a}, {"out": a})).verdict == "CONSERVED")
        u = float(rng.uniform(0.05, 1.0))
        ou_ok += (en.govern(en.EnergyLedger("ou", {"in": a}, {"out": a*(1+u)})).verdict
                  == "VIOLATION_CREATION")
    P["energy_conserved_correct"] = {"held": cons_ok, "trials": N, "rate": cons_ok/N}
    P["energy_overunity_refused"] = {"held": ou_ok, "trials": N, "rate": ou_ok/N}
    print(f"  ENERGY  conserved ledgers → CONSERVED        : {cons_ok}/{N}")
    print(f"  ENERGY  over-unity ledgers → VIOLATION_CREATION: {ou_ok}/{N}")

    # --- flow: injected leak/fabrication detected at the right stage ----------
    import flow_conservation as fc
    rng = np.random.default_rng(1)
    flow_ok = M = 0
    for _ in range(3000):
        k = int(rng.integers(3, 8)); j = int(rng.integers(0, k))
        kind = "leak" if rng.random() < 0.5 else "fab"
        delta = float(rng.uniform(5, 50)) * (-1 if kind == "leak" else 1)
        stages, entry = [], 1000.0
        for s in range(k):
            exit_ = entry + (delta if s == j else 0.0)
            stages.append(fc.Stage(f"s{s}", entry, exit_))
            entry = exit_
        rep = fc.govern(tuple(stages))
        want = "LEAK" if kind == "leak" else "FABRICATION"
        M += 1
        flow_ok += (rep.verdict == want and rep.first_break == f"s{j}")
    P["flow_detection_accuracy"] = {"held": flow_ok, "trials": M, "rate": flow_ok/M}
    print(f"  FLOW  leak/fabrication detected at correct stage: {flow_ok}/{M}")

    # --- duality: derived check flagged; independent passes -------------------
    import duality_governor as dg
    rng = np.random.default_rng(2)
    circ_ok = indep_ok = D = 0
    for _ in range(2000):
        claim = tuple(float(v) for v in rng.normal(100, 5, 12))
        a = float(rng.uniform(0.5, 2)); b = float(rng.uniform(-5, 5))
        derived = tuple(a*v + b for v in claim)
        D += 1
        circ_ok += (dg.govern(dg.Duality("d", claim, "s1", derived, "s2")).verdict
                    == "SUSPECTED_CIRCULAR")
        indep = tuple(float(v) for v in rng.normal(100, 5, 12))
        indep_ok += (dg.govern(dg.Duality("i", claim, "s1", indep, "s2")).verdict
                     == "GROUNDED_DUALITY")
    P["duality_circular_caught"] = {"held": circ_ok, "trials": D, "rate": circ_ok/D}
    P["duality_independent_passed"] = {"held": indep_ok, "trials": D, "rate": indep_ok/D}
    print(f"  DUALITY  derived check → SUSPECTED_CIRCULAR   : {circ_ok}/{D}")
    print(f"  DUALITY  independent check → GROUNDED_DUALITY : {indep_ok}/{D}")

    # --- ravens: any white ⇒ REFUTED; greens never inflate genuine count ------
    import green_raven as gr
    rng = np.random.default_rng(3)
    raven_ok = greens_excluded_ok = R = 0
    for _ in range(2000):
        obs, n_black = [], 0
        for _ in range(int(rng.integers(1, 12))):
            roll = rng.random()
            if roll < 0.4:
                obs.append(gr.Observation("b", "upheld", exercises_claim=True)); n_black += 1
            elif roll < 0.8:
                obs.append(gr.Observation("g", "upheld", exercises_claim=False))     # vacuous
            else:
                obs.append(gr.Observation("w", "violated"))
        rep = gr.assess("claim", obs)
        has_white = any(o.result == "violated" for o in obs)
        R += 1
        raven_ok += ((rep.verdict == "REFUTED") == has_white)
        greens_excluded_ok += (rep.genuine_confirmations == n_black)   # greens never counted
    P["raven_white_refutes"] = {"held": raven_ok, "trials": R, "rate": raven_ok/R}
    P["raven_greens_excluded"] = {"held": greens_excluded_ok, "trials": R, "rate": greens_excluded_ok/R}
    print(f"  RAVEN  (white present ⇔ REFUTED)              : {raven_ok}/{R}")
    print(f"  RAVEN  green ravens excluded from count       : {greens_excluded_ok}/{R}")

    # --- bounded_process: terminating vs non-terminating vs no-beginning ------
    import bounded_process as bp
    rng = np.random.default_rng(4)
    bp_ok = B = 0
    for _ in range(2000):
        n = int(rng.integers(1, 50))
        term = bp.Process("cd", seed=n, step=lambda k: k-1, is_halt=lambda k: k <= 0)
        forever = bp.Process("f", seed=0, step=lambda k: k+1, is_halt=lambda k: False, max_steps=n)
        B += 1
        bp_ok += (bp.govern(term).verdict == "WELL_BOUNDED"
                  and bp.govern(forever).verdict == "NO_END")
    P["bounded_process_classification"] = {"held": bp_ok, "trials": B, "rate": bp_ok/B}
    print(f"  BOUNDED  terminating→WELL_BOUNDED & forever→NO_END: {bp_ok}/{B}")

    # --- temporal: the future is never certifiable ---------------------------
    import temporal_governor as tg
    tem_ok = T = 0
    for seed in range(500):
        T += 1
        try:
            tg.certify_future(tg.TemporalClaim("x", tg.FUTURE, forecast_prob=0.5))
        except tg.FutureCertificationRefused:
            tem_ok += 1
    P["temporal_future_never_certified"] = {"held": tem_ok, "trials": T, "rate": tem_ok/T}
    print(f"  TEMPORAL  certify_future always refused       : {tem_ok}/{T}")

    # --- gene_shift: drift alert, gap discontinuity, lead time ---------------
    # Three structural invariants over 500 seeded realisations of the
    # drift-then-shift immune-proxy scenario:
    #   (a) alert always fires during the drift phase (before the shift event)
    #   (b) the shift event always widens the proxy/truth gap beyond the drift peak
    #   (c) the alert precedes immune failure (positive lead time) in ≥98% of runs
    import gene_shift_infra as gs
    gs_alert_in_drift = gs_shift_wider = gs_lead_positive = GS = 0
    for seed in range(500):
        _, _, r = gs.analyse(seed=seed)
        GS += 1
        gs_alert_in_drift += (r["alert"] is not None and r["alert"] < 40)
        gs_shift_wider    += (r["gap"][40] > r["gap"][:40].max())
        gs_lead_positive  += (r["lead"] is not None and r["lead"] > 0)
    P["gene_shift_alert_in_drift"]  = {"held": int(gs_alert_in_drift), "trials": GS,
                                        "rate": gs_alert_in_drift / GS}
    P["gene_shift_gap_discontinuous"] = {"held": int(gs_shift_wider), "trials": GS,
                                          "rate": gs_shift_wider / GS}
    P["gene_shift_lead_positive"]   = {"held": int(gs_lead_positive), "trials": GS,
                                        "rate": gs_lead_positive / GS}
    print(f"  GENE_SHIFT  alert during drift phase (a<40)  : {gs_alert_in_drift}/{GS}")
    print(f"  GENE_SHIFT  shift widens gap discontinuously : {gs_shift_wider}/{GS}")
    print(f"  GENE_SHIFT  positive lead before failure     : {gs_lead_positive}/{GS}"
          f"  ({'100%' if gs_lead_positive==GS else f'{100*gs_lead_positive/GS:.1f}%'})")

    RESULTS["phase3_properties"] = P


# ---------------------------------------------------------------------------
# Phase 4 — edge cases (must not crash; sensible verdicts)
# ---------------------------------------------------------------------------
def phase4_edge():
    _hdr("PHASE 4 — edge cases (degenerate inputs must not crash)")
    import flow_conservation as fc, duality_governor as dg, energy_matter as en
    import em_estimation as em, freedom_infra as fi
    cases, ok = [], 0

    def run(name, fn):
        nonlocal ok
        try:
            v = fn(); cases.append((name, True, str(v))); ok += 1
        except Exception as ex:
            cases.append((name, False, f"{type(ex).__name__}: {ex}"))

    run("flow: empty pipeline", lambda: fc.govern(())._asdict() if hasattr(fc.govern(()), "_asdict")
        else fc.govern(()).verdict)
    run("duality: length-1 series", lambda: dg.govern(dg.Duality("d", (1.0,), "s1", (2.0,), "s2")).verdict)
    run("duality: no check side", lambda: dg.govern(dg.Duality("d", (1.0, 2.0), "s1")).verdict)
    run("energy: all zero", lambda: en.govern(en.EnergyLedger("z", {"in": 0.0}, {"out": 0.0})).verdict)
    run("energy: huge values", lambda: en.govern(en.EnergyLedger("h", {"in": 1e18}, {"out": 1e18})).verdict)
    run("em: tiny n=6", lambda: em.govern("t", em._mixture(0, (-5.0, 5.0), n=6)).verdict)
    run("freedom: no options", lambda: fi.govern(fi.FreedomCase("e", ())).verdict)

    for name, good, detail in cases:
        print(f"  [{'OK ' if good else 'ERR'}] {name:<28} → {detail}")
    print(f"  {ok}/{len(cases)} edge cases handled without crashing.")
    RESULTS["phase4_edge"] = {"total": len(cases), "handled": ok,
                              "cases": [{"case": n, "ok": g, "detail": d} for n, g, d in cases]}


# ---------------------------------------------------------------------------
# Phase 5 — performance (ops/sec on hot paths)
# ---------------------------------------------------------------------------
def phase5_perf():
    _hdr("PHASE 5 — performance (throughput on hot paths)")
    import duality_governor as dg, energy_matter as en, temporal_governor as tg
    import fractal_recursion as fr, flow_conservation as fc, postmortem_infra as pm
    import em_estimation as em

    claim = tuple(float(i) for i in range(12)); chk = tuple(2.0*i for i in range(12))
    stages = tuple(fc.Stage(f"s{i}", 100.0, 100.0) for i in range(6))
    cant = fr.catalogue()[2]
    import gene_shift_infra as gs
    _gs_proxy, _gs_truth = gs.drift_then_shift_series(seed=42)
    bench = {
        "duality.govern": (lambda: dg.govern(dg.Duality("d", claim, "a", chk, "b")), 20000),
        "energy.govern": (lambda: en.govern(en.EnergyLedger("c", {"i": 100.0}, {"o": 100.0})), 20000),
        "temporal.govern": (lambda: tg.govern(tg.TemporalClaim("x", tg.FUTURE, forecast_prob=0.3)), 20000),
        "fractal.sim_dimension": (lambda: fr.similarity_dimension(cant), 100000),
        "flow.govern(6 stages)": (lambda: fc.govern(stages), 20000),
        "em.fit_em(n=400)": (lambda: em.fit_em(em._mixture(0, (-5.0, 5.0)), seed=0), 50),
        "gene_shift.monitor(n=60)": (lambda: gs.dm.monitor(_gs_proxy, _gs_truth, cfg=gs.GENE_CFG), 2000),
    }
    rows = {}
    for name, (fn, n) in bench.items():
        t0 = time.perf_counter()
        for _ in range(n):
            fn()
        dt = time.perf_counter() - t0
        ops = n / dt
        rows[name] = {"n": n, "secs": round(dt, 4), "ops_per_sec": round(ops, 1),
                      "us_per_op": round(1e6 * dt / n, 2)}
        print(f"  {name:<26} {ops:>12,.0f} ops/s   ({1e6*dt/n:>8.2f} µs/op, n={n})")
    RESULTS["phase5_perf"] = rows


if __name__ == "__main__":
    _hdr("GOVERNANCE TOOLKIT — EMPIRICAL STRESS TEST")
    passed = phase1_selftests()
    phase2_determinism(passed)
    phase3_properties()
    phase4_edge()
    phase5_perf()
    with open(os.path.join(ROOT, "stress_results.json"), "w") as f:
        json.dump(RESULTS, f, indent=2)
    _hdr("DONE — machine-readable results in stress_results.json")
