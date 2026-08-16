"""
_fix2.py — Second-pass fixes for cases _refactor.py didn't fully handle.

Run:  python _fix2.py [--dry-run]

Handles
-------
A) Group B check closures: def check(name, condition) with nonlocal → tr.ok()
B) Group C check closures: def check(label, got, expected) with nonlocal → tr.expect()
   Also handles def checkclose(label, got, expected, tol) → rewrite in-place
C) Group C summary block: total = passed + failed ... → return not tr.summary()
D) reconciliation_infra.py: global _pass/_fail, if __name__ == "__main__" structure
E) dimensional_governor.py: _clamp01 function reference not renamed
F) meta_omega7_infra.py, pr_topology.py: import inserted inside multi-line import
G) recursive_sos_federation.py: pre-existing Generator SyntaxError
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
        print(f"  [DRY] would fix {path}")
        return
    open(path, "w", encoding="utf-8").write(src)
    print(f"  fixed {path}")


# ── Remove closures that use nonlocal passed, failed ─────────────────────────

def _remove_nonlocal_closures(src: str) -> str:
    """Remove def X(...)  closures that declare 'nonlocal passed, failed'."""
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
                # Drop the preceding blank separator line
                if out and out[-1].strip() == '':
                    out.pop()
                continue

        if in_closure:
            if stripped == '' or cur_indent > closure_indent:
                continue  # still inside closure body
            else:
                in_closure = False  # first non-blank at same/lower indent → done

        out.append(line)

    return '\n'.join(out)


def _remove_global_closures(src: str) -> str:
    """Remove def X(...)  closures that declare 'global _pass, _fail'."""
    lines = src.split('\n')
    out = []
    in_closure = False
    closure_indent = None

    for i, line in enumerate(lines):
        stripped = line.lstrip()
        cur_indent = len(line) - len(stripped)

        if not in_closure and stripped.startswith('def ') and cur_indent >= 4:
            lookahead = '\n'.join(lines[i: min(i + 6, len(lines))])
            if 'global _pass, _fail' in lookahead:
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


# ── Rewrite checkclose in-place (doesn't use nonlocal) ────────────────────────

def _rewrite_checkclose(src: str) -> str:
    """
    Rewrite the checkclose closure body to use tr.ok instead of counters.
    Expects the closure to look like:
        def checkclose(label: str, got: float, expected: float, tol: float = 1e-9) -> None:
            nonlocal passed, failed
            if abs(got - expected) <= tol:
                passed += 1
            else:
                failed += 1
    """
    return re.sub(
        r'(    def checkclose\([^)]*\) -> None:)\s*nonlocal passed, failed\s*'
        r'if abs\(got - expected\) <= tol:\s*passed \+= 1\s*else:\s*failed \+= 1',
        r'\1\n        tr.ok(label, abs(got - expected) <= tol)',
        src,
        flags=re.DOTALL,
    )


# ── Initialize tr at start of _run_tests ─────────────────────────────────────

def _insert_tr_into_run_tests(src: str, suite_name: str, verbose: bool = True) -> str:
    """
    Insert  tr = TestRunner(suite_name[, verbose=False])  and  tr.header()
    right at the start of the _run_tests function body (after the def line).
    """
    v_arg = "" if verbose else ", verbose=False"
    tr_block = f"\n    tr = TestRunner({suite_name!r}{v_arg})\n    tr.header()\n"

    # If there's already a tr assignment, skip
    if 'tr = TestRunner' in src:
        return src

    # Insert after "def _run_tests(...):\n" (right after the opening blank line)
    return re.sub(
        r'(def _run_tests\([^)]*\)[^:]*:\n)\n',
        r'\1' + tr_block + '\n',
        src,
        count=1,
    )


def _replace_print_banner_with_tr(src: str, suite_name: str, verbose: bool = True) -> str:
    """
    Replace  print("=== ... ===\n")  banner with  tr = TestRunner(...); tr.header().
    Used for Group B files which have a single-line print banner.
    """
    if 'tr = TestRunner' in src:
        return src

    v_arg = "" if verbose else ", verbose=False"
    replacement = (
        f"    tr = TestRunner({suite_name!r}{v_arg})\n"
        f"    tr.header()"
    )
    # Match: print("=== ... ===\n") with optional \n  at the end of line
    new_src = re.sub(
        r'    print\("=== .*? ===\\n"\)',
        replacement,
        src,
        count=1,
    )
    return new_src


# ── Summary block replacement ─────────────────────────────────────────────────

# Pattern C: total = passed + failed ... return failed == 0
_SUMMARY_TOTAL = re.compile(
    r'\n    print\("\\n" \+ "=" \* 62\)\n'
    r'    total = passed \+ failed\n'
    r'    print\(f"Results: \{passed\}/\{total\} passed", .*?\)\n'
    r'    if failed:\n'
    r'        print\(f"  \{failed\} test\(s\) FAILED"\)\n'
    r'    print\("=" \* 62\)\n'
    r'    return failed == 0',
    re.DOTALL,
)

# Pattern B: print(f"\n{'='*50}") ... raise SystemExit(f"...")
_SUMMARY_RAISE = re.compile(
    r"\n    print\(f\"\\n\{['\"]=['\"] \* \d+\}\"\)\n"
    r"    print\(f\"Results: \{passed\} passed, \{failed\} failed out of \{passed \+ failed\} tests\"\)\n"
    r"    if failed == 0:\n"
    r"        print\(\"ALL TESTS PASSED\"\)\n"
    r"    else:\n"
    r"        raise SystemExit\(.*?\)",
    re.DOTALL,
)

# Pattern C-custom: print(f"\n{module}: {passed} passed...") + if failed: raise SystemExit(1)
_SUMMARY_CUSTOM = re.compile(
    r'\n    print\(f"\\n[^"]+: \{passed\} passed, \{failed\} failed '\
    r'"\n          f"\([^"]+\)"\)\n'
    r'    if failed:\n'
    r'        raise SystemExit\(1\)',
    re.DOTALL,
)

# Second variant of custom (single-line print)
_SUMMARY_CUSTOM2 = re.compile(
    r'\n    print\(f"\\n[^"]+: \{passed\} passed, \{failed\} failed [^"]+"\)\n'
    r'    if failed:\n'
    r'        raise SystemExit\(1\)',
    re.DOTALL,
)


def _replace_summary(src: str) -> str:
    """Replace known summary block patterns with tr.summary()."""
    # Pattern C (total=passed+failed, return failed==0)
    src = _SUMMARY_TOTAL.sub("\n    return not tr.summary()", src)

    # Pattern B (print({...}), raise SystemExit)
    src = _SUMMARY_RAISE.sub(
        "\n    if tr.summary():\n        raise SystemExit(1)",
        src,
    )

    # Pattern C-custom (multiline print with passed+failed, raise SystemExit(1))
    src = _SUMMARY_CUSTOM.sub(
        "\n    if tr.summary():\n        raise SystemExit(1)",
        src,
    )
    src = _SUMMARY_CUSTOM2.sub(
        "\n    if tr.summary():\n        raise SystemExit(1)",
        src,
    )

    return src


def _replace_summary_generic(src: str) -> str:
    """
    Generic fallback: remove any block that only references passed/failed
    at the end of _run_tests and replace with tr.summary().
    Works by finding the last 'if failed' or 'if passed' block before the
    function ends.
    """
    # Match the specific bio-style summary
    src = re.sub(
        r'\n    print\(f"\\n\w+(?:_infra|_federation)?: \{passed\} passed, \{failed\} failed '
        r'"\s*f"\([^)]+\)%\)"\)\n    if failed:\n        raise SystemExit\(1\)',
        "\n    if tr.summary():\n        raise SystemExit(1)",
        src,
        flags=re.DOTALL,
    )
    return src


# ── Group-level patches ───────────────────────────────────────────────────────

# Group B: def check(name, condition) → tr.ok, verbose TestRunner
GROUP_B_CHECK = [
    ("digital_generation_detector_infra.py",   "digital_generation_detector_infra  —  unit tests"),
    ("incalculable_infra.py",                   "incalculable_infra  —  unit tests"),
    ("math_break_infra.py",                     "math_break_infra  —  unit tests"),
    ("meta_singular_math_ontology_infra.py",    "meta_singular_math_ontology_infra  —  unit tests"),
    ("poly_federation_mesh_infra.py",           "poly_federation_mesh_infra  —  unit tests"),
    ("resonance_coherence_infra.py",            "resonance_coherence_infra  —  unit tests"),
    ("singularity_reemergence_infra.py",        "singularity_reemergence_infra  —  unit tests"),
    ("stress_edge_case_infra.py",               "stress_edge_case_infra  —  unit tests"),
    ("stress_test_infra.py",                    "stress_test_infra  —  unit tests"),
]

# Group C: def check(label, got, expected) → tr.expect, silent TestRunner
GROUP_C_CHECK = [
    ("bio_signal_infra.py",              "bio_signal_infra.py — Test Suite"),
    ("eye_movement_infra.py",            "eye_movement_infra.py — Test Suite"),
    ("llm_ui_infra.py",                  "llm_ui_infra.py — Test Suite"),
    ("logic_signal_infra.py",            "logic_signal_infra.py — Test Suite"),
    ("movement_infra.py",                "movement_infra.py — Test Suite"),
    ("predictive_recursion_infra.py",    "predictive_recursion_infra.py — Test Suite"),
    ("sound_infra.py",                   "sound_infra.py — Test Suite"),
    ("time_infra.py",                    "time_infra.py — Test Suite"),
    ("visual_infra.py",                  "visual_infra.py — Test Suite"),
]

# Group C summary-only (check closure already removed, just need summary fixed)
GROUP_C_SUMMARY = [
    "em_signal_mixing_infra.py",
    "em_signal_mixing_detector_infra.py",
    "pattern_analytic_infra.py",
    "pattern_drift_infra.py",
    "pattern_trap_infra.py",
    "recursive_biology_federation.py",
    "recursive_emergence_federation.py",
    "recursive_sociology_federation.py",
    "swarm_mesh_federation.py",
]


def patch_group_b_check():
    print("\n=== Group B: def check(name, condition) → tr.ok ===")
    for fname, suite_name in GROUP_B_CHECK:
        if not os.path.exists(fname):
            print(f"  SKIP (not found): {fname}")
            continue
        src = read(fname)

        # Remove def check(name, condition) closures
        src = _remove_nonlocal_closures(src)

        # Initialize tr (replace print banner or insert at start)
        src = _replace_print_banner_with_tr(src, suite_name, verbose=True)
        # Fallback: insert at start of _run_tests if banner didn't match
        src = _insert_tr_into_run_tests(src, suite_name, verbose=True)

        # Replace check( → tr.ok(
        src = re.sub(r'\bcheck\(', 'tr.ok(', src)

        # Replace summary
        src = _replace_summary(src)
        src = _replace_summary_generic(src)

        write(fname, src)


def patch_group_c_check():
    print("\n=== Group C: def check(label, got, expected) → tr.expect ===")
    for fname, suite_name in GROUP_C_CHECK:
        if not os.path.exists(fname):
            print(f"  SKIP (not found): {fname}")
            continue
        src = read(fname)

        # Special case: predictive_recursion has checkclose too
        if fname == "predictive_recursion_infra.py":
            src = _rewrite_checkclose(src)

        # Remove def check(label, got, expected) closures
        src = _remove_nonlocal_closures(src)

        # Initialize tr (silent, no banner in these files)
        src = _insert_tr_into_run_tests(src, suite_name, verbose=False)

        # Replace check( → tr.expect(  (BEFORE replacing any ok( to avoid double-replace)
        src = re.sub(r'\bcheck\(', 'tr.expect(', src)

        # Replace summary
        src = _replace_summary(src)
        src = _replace_summary_generic(src)

        write(fname, src)


def patch_group_c_summary():
    print("\n=== Group C summary-only: replace total=passed+failed block ===")
    for fname in GROUP_C_SUMMARY:
        if not os.path.exists(fname):
            print(f"  SKIP (not found): {fname}")
            continue
        src = read(fname)
        new_src = _replace_summary(src)
        new_src = _replace_summary_generic(new_src)
        if new_src == src:
            print(f"  WARN (no change): {fname}")
        else:
            write(fname, new_src)


# ── reconciliation_infra.py ───────────────────────────────────────────────────

def patch_reconciliation():
    print("\n=== reconciliation_infra.py ===")
    fname = "reconciliation_infra.py"
    if not os.path.exists(fname):
        print(f"  SKIP (not found)")
        return
    src = read(fname)

    # 1. Remove _pass = _fail = 0
    src = re.sub(r'    _pass = _fail = 0\n', '', src)

    # 2. Remove def check(desc, cond) with global _pass, _fail
    src = _remove_global_closures(src)

    # 3. Replace the banner print("=" * 58) / name / print("=" * 58)
    src = re.sub(
        r'    print\("=" \* 58\)\n'
        r'    print\("reconciliation_infra  —  unit tests"\)\n'
        r'    print\("=" \* 58\)',
        '    tr = TestRunner("reconciliation_infra  —  unit tests")\n    tr.header()',
        src,
        count=1,
    )

    # 4. Replace check( → tr.ok(
    src = re.sub(r'\bcheck\(', 'tr.ok(', src)

    # 5. Replace _pass and _fail summary at the end
    src = re.sub(
        r'    print\(\)\n'
        r'    print\("=" \* 58\)\n'
        r'    print\(f"Results: \{_pass\} passed, \{_fail\} failed out of \{_pass \+ _fail\} tests"\)\n'
        r'    if _fail == 0:\n'
        r'        print\("ALL TESTS PASSED"\)\n'
        r'    else:\n'
        r'        print\(f"FAILURES: \{_fail\}"\)',
        '    tr.summary()',
        src,
    )

    write(fname, src)


# ── dimensional_governor.py ───────────────────────────────────────────────────

def patch_dimensional_governor():
    print("\n=== dimensional_governor.py ===")
    fname = "dimensional_governor.py"
    if not os.path.exists(fname):
        print("  SKIP (not found)")
        return
    src = read(fname)

    # Replace _clamp01 used as a function reference (without parens)
    # Pattern: _clamp01, (inside _specs tuple)
    src = re.sub(r'\b_clamp01\b', '_c01', src)

    # Also: the local def _c01 at line 235 shadows the import but it's fine
    # (it's a test subject, not the utility — leave it)

    write(fname, src)


# ── meta_omega7_infra.py and pr_topology.py ──────────────────────────────────

def patch_bad_imports():
    print("\n=== Fix imports injected inside multi-line imports ===")
    for fname in ("meta_omega7_infra.py", "pr_topology.py"):
        if not os.path.exists(fname):
            print(f"  SKIP (not found): {fname}")
            continue
        src = read(fname)

        # Remove the misplaced 'from governance_core import TestRunner' line
        # that was inserted inside a multi-line import
        lines = src.split('\n')
        new_lines = []
        removed = False
        for line in lines:
            if line.strip() == 'from governance_core import TestRunner' and not removed:
                # Check if the PREVIOUS non-blank line starts a multi-line import
                # (i.e., ends with '(')
                prev = next((l for l in reversed(new_lines) if l.strip()), '')
                if prev.endswith('(') or ('import (' in prev):
                    removed = True
                    continue  # drop this misplaced line
            new_lines.append(line)

        src = '\n'.join(new_lines)

        # Now insert 'from governance_core import TestRunner' before the
        # multi-line import that it was accidentally injected into
        if 'from governance_core import TestRunner' not in src:
            # Insert before the first 'from xxx import (' line
            src = re.sub(
                r'(\nfrom \w[^\n]+ import \()',
                '\nfrom governance_core import TestRunner\n'
                r'\1',
                src,
                count=1,
            )

        write(fname, src)


# ── recursive_sos_federation.py ───────────────────────────────────────────────

def patch_recursive_sos():
    print("\n=== recursive_sos_federation.py: Generator parenthesization ===")
    fname = "recursive_sos_federation.py"
    if not os.path.exists(fname):
        print("  SKIP (not found)")
        return
    src = read(fname)

    # Fix: max(gen_expr for ..., key=...) → max((gen_expr for ...), key=...)
    src = re.sub(
        r'return max\(e\.interop_level for e in self\.interop_edges,',
        'return max((e.interop_level for e in self.interop_edges),',
        src,
    )

    write(fname, src)


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    patch_group_b_check()
    patch_group_c_check()
    patch_group_c_summary()
    patch_reconciliation()
    patch_dimensional_governor()
    patch_bad_imports()
    patch_recursive_sos()

    print("\nDone. Run tests to verify.")
