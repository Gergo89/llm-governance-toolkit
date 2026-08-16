"""
_fix3.py — Third-pass targeted fixes for remaining issues after _fix2.py.

Issues addressed:
  1. Group C check files: tr not initialized (blank line was eaten by closure removal)
  2. Group B check files: summary block not replaced (regex spacing issue)
  3. singularity_reemergence + meta_singular: corrupted summary (wrong greedy match)
  4. math_break_infra.py: production code check( → tr.ok( wrongly replaced
  5. predictive_recursion_infra.py: orphaned print() after checkclose rewrite
  6. meta_omega7_infra.py: check closure still there (missed in _fix2.py)
  7. recursive_sos_federation.py: summary not replaced (missed in _fix2.py)
"""

from __future__ import annotations
import re
import sys
import os

DRY = "--dry-run" in sys.argv


def read(path: str) -> str:
    return open(path, encoding="utf-8").read()


def write(path: str, src: str) -> None:
    if DRY:
        print(f"  [DRY] {path}")
        return
    open(path, "w", encoding="utf-8").write(src)
    print(f"  fixed {path}")


# ── 1. Insert tr even when there's no blank line after def _run_tests(): ─────

def _ensure_tr_initialized(src: str, suite_name: str, verbose: bool = False) -> str:
    """Insert tr = TestRunner(...) at the start of _run_tests if not already there."""
    if 'tr = TestRunner' in src:
        return src
    v_arg = "" if verbose else ", verbose=False"
    tr_lines = (
        f"    tr = TestRunner({suite_name!r}{v_arg})\n"
        f"    tr.header()\n\n"
    )
    # Insert right after "def _run_tests...:\n" — with or without following blank line
    return re.sub(
        r'(def _run_tests\([^)]*\)[^:]*:\n)\n?',
        r'\1' + tr_lines,
        src,
        count=1,
    )


GROUP_C_CHECK_SUITES = {
    "bio_signal_infra.py":              "bio_signal_infra.py — Test Suite",
    "eye_movement_infra.py":            "eye_movement_infra.py — Test Suite",
    "llm_ui_infra.py":                  "llm_ui_infra.py — Test Suite",
    "logic_signal_infra.py":            "logic_signal_infra.py — Test Suite",
    "movement_infra.py":                "movement_infra.py — Test Suite",
    "predictive_recursion_infra.py":    "predictive_recursion_infra.py — Test Suite",
    "sound_infra.py":                   "sound_infra.py — Test Suite",
    "time_infra.py":                    "time_infra.py — Test Suite",
    "visual_infra.py":                  "visual_infra.py — Test Suite",
}


def fix_group_c_tr():
    print("\n=== Fix 1: Group C — initialize tr in _run_tests ===")
    for fname, suite_name in GROUP_C_CHECK_SUITES.items():
        if not os.path.exists(fname):
            print(f"  SKIP: {fname}")
            continue
        src = read(fname)
        new_src = _ensure_tr_initialized(src, suite_name, verbose=False)
        if new_src == src:
            print(f"  no-change: {fname}")
        else:
            write(fname, new_src)


# ── 2. Group B summary: replace the 5-line block ─────────────────────────────

_SUMMARY_B = re.compile(
    r"    print\(f\"\\n\{[^}]+\}\"\)\n"
    r"    print\(f\"Results: \{passed\} passed, \{failed\} failed out of \{passed \+ failed\} tests\"\)\n"
    r"    if failed == 0:\n"
    r"        print\(\"ALL TESTS PASSED\"\)\n"
    r"    else:\n"
    r"        raise SystemExit\(f\"[^\"]+\"\)",
)

GROUP_B_SUMMARY_FILES = [
    "digital_generation_detector_infra.py",
    "incalculable_infra.py",
    "poly_federation_mesh_infra.py",
    "resonance_coherence_infra.py",
    "stress_edge_case_infra.py",
    "stress_test_infra.py",
]


def fix_group_b_summary():
    print("\n=== Fix 2: Group B — replace print-based summary with tr.summary() ===")
    for fname in GROUP_B_SUMMARY_FILES:
        if not os.path.exists(fname):
            print(f"  SKIP: {fname}")
            continue
        src = read(fname)
        new_src = _SUMMARY_B.sub(
            '    if tr.summary():\n        raise SystemExit(1)',
            src,
        )
        if new_src == src:
            print(f"  WARN no-change: {fname}")
        else:
            write(fname, new_src)


# ── 3. Repair corrupted summary lines ────────────────────────────────────────

def fix_corrupted_summaries():
    print("\n=== Fix 3: Repair corrupted summary lines ===")
    for fname in ("singularity_reemergence_infra.py", "meta_singular_math_ontology_infra.py"):
        if not os.path.exists(fname):
            print(f"  SKIP: {fname}")
            continue
        src = read(fname)
        # The corruption is: raise SystemExit(1) failed")
        # where the regex matched up to the ) in test(s) and left  failed") behind.
        # Full corrupted block (as produced by _fix2.py):
        #   if tr.summary():
        #       raise SystemExit(1) failed")
        new_src = src.replace(
            '    if tr.summary():\n        raise SystemExit(1) failed")',
            '    if tr.summary():\n        raise SystemExit(1)',
        )
        if new_src == src:
            print(f"  WARN no-change: {fname}")
        else:
            write(fname, new_src)


# ── 4. Fix math_break_infra.py: revert production check( → tr.ok( ────────────

def fix_math_break():
    print("\n=== Fix 4: math_break_infra.py — revert production tr.ok( in list comp ===")
    fname = "math_break_infra.py"
    if not os.path.exists(fname):
        print("  SKIP")
        return
    src = read(fname)
    # The specific corrupted line:
    # failures = [r for check in checks for r in [tr.ok(signal)] if r is not None]
    new_src = src.replace(
        "    failures = [r for check in checks for r in [tr.ok(signal)] if r is not None]",
        "    failures = [r for check in checks for r in [check(signal)] if r is not None]",
    )
    if new_src == src:
        print("  WARN no-change")
    else:
        write(fname, new_src)

    # Also fix summary if not yet replaced
    new_src2 = _SUMMARY_B.sub(
        '    if tr.summary():\n        raise SystemExit(1)',
        new_src,
    )
    if new_src2 != new_src:
        write(fname, new_src2)
        new_src = new_src2


# ── 5. Fix predictive_recursion_infra.py: orphaned print after checkclose ─────

def fix_predictive_recursion():
    print("\n=== Fix 5: predictive_recursion_infra.py — remove orphaned print line ===")
    fname = "predictive_recursion_infra.py"
    if not os.path.exists(fname):
        print("  SKIP")
        return
    src = read(fname)
    # The orphaned line appears right after checkclose rewrite:
    #     def checkclose(...) -> None:
    #         tr.ok(label, abs(got - expected) <= tol)
    #             print(f"  FAIL {label}: got {got!r}, expected ≈{expected!r} (±{tol})")
    # Remove the indented print line after tr.ok(label, ...)
    new_src = re.sub(
        r'(        tr\.ok\(label, abs\(got - expected\) <= tol\)\n)'
        r'            print\(f"  FAIL \{label\}:.*?"\)\n',
        r'\1',
        src,
    )
    if new_src == src:
        print("  WARN no-change")
    else:
        write(fname, new_src)

    # Also add tr initialization since it's a Group C file
    suite_name = "predictive_recursion_infra.py — Test Suite"
    new_src2 = _ensure_tr_initialized(new_src if new_src != src else src, suite_name, verbose=False)
    if new_src2 != (new_src if new_src != src else src):
        write(fname, new_src2)


# ── 6. meta_omega7_infra.py: still has check closure ────────────────────────

def _remove_nonlocal_closures(src: str) -> str:
    lines = src.split('\n')
    out = []
    in_closure = False
    closure_indent = None
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        cur_indent = len(line) - len(stripped)
        if not in_closure and stripped.startswith('def ') and cur_indent >= 4:
            lookahead = '\n'.join(lines[i: min(i + 8, len(lines))])
            if 'nonlocal passed, failed' in lookahead:
                in_closure = True
                closure_indent = cur_indent
                if out and out[-1].strip() == '':
                    out.pop()
                continue
        if in_closure:
            if stripped == '' or cur_indent > closure_indent:
                continue
            else:
                in_closure = False
        out.append(line)
    return '\n'.join(out)


def fix_meta_omega7():
    print("\n=== Fix 6: meta_omega7_infra.py — apply Group B check fix ===")
    fname = "meta_omega7_infra.py"
    if not os.path.exists(fname):
        print("  SKIP")
        return
    src = read(fname)
    suite_name = "meta_omega7_infra  —  unit tests"

    # Remove check(name, condition) closure
    src = _remove_nonlocal_closures(src)

    # Replace print banner with tr initialization
    src = re.sub(
        r'    print\("=== meta_omega7_infra tests ===\\n"\)',
        f'    tr = TestRunner({suite_name!r})\n    tr.header()',
        src,
        count=1,
    )
    # Fallback: insert tr at start of _run_tests
    src = _ensure_tr_initialized(src, suite_name, verbose=True)

    # Replace check( → tr.ok(
    src = re.sub(r'\bcheck\(', 'tr.ok(', src)

    # Replace summary
    src = _SUMMARY_B.sub('    if tr.summary():\n        raise SystemExit(1)', src)

    write(fname, src)


# ── 7. recursive_sos_federation.py: summary not replaced ─────────────────────

_SUMMARY_TOTAL = re.compile(
    r'    print\("\\n" \+ "=" \* 62\)\n'
    r'    total = passed \+ failed\n'
    r'    print\(f"Results: \{passed\}/\{total\} passed", .*?\)\n'
    r'    if failed:\n'
    r'        print\(f"  \{failed\} test\(s\) FAILED"\)\n'
    r'    print\("=" \* 62\)\n'
    r'    return failed == 0',
)


def fix_recursive_sos():
    print("\n=== Fix 7: recursive_sos_federation.py — replace summary ===")
    fname = "recursive_sos_federation.py"
    if not os.path.exists(fname):
        print("  SKIP")
        return
    src = read(fname)
    new_src = _SUMMARY_TOTAL.sub('    return not tr.summary()', src)
    if new_src == src:
        print("  WARN no-change")
    else:
        write(fname, new_src)


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    fix_group_c_tr()
    fix_group_b_summary()
    fix_corrupted_summaries()
    fix_math_break()
    fix_predictive_recursion()
    fix_meta_omega7()
    fix_recursive_sos()
    print("\nDone.")
