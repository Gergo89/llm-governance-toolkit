"""
_refactor.py — apply governance_core imports to all infra modules.

Run:  python _refactor.py [--dry-run]

Groups
------
A  Files with inline _sf/_c01 AND verbose TestRunner (PASS+FAIL format)
B  Files with verbose TestRunner but no inline helpers
C  Files with silent TestRunner (FAIL-only, legacy compact format)
"""

from __future__ import annotations
import re
import sys
import os

DRY = "--dry-run" in sys.argv

# ─────────────────────────────────────────────────────────────────────────────
# Helper: read / write
# ─────────────────────────────────────────────────────────────────────────────

def read(path):
    return open(path, encoding="utf-8").read()


def write(path, src):
    if DRY:
        print(f"  [DRY] would write {path}")
        return
    open(path, "w", encoding="utf-8").write(src)
    print(f"  wrote {path}")


# ─────────────────────────────────────────────────────────────────────────────
# Patch helpers: add core import after the last stdlib import block
# ─────────────────────────────────────────────────────────────────────────────

CORE_IMPORT_SF    = "from governance_core import _sf, _c01, _log_ratio, _binding, TestRunner"
CORE_IMPORT_C01   = "from governance_core import _c01, TestRunner"
CORE_IMPORT_TR    = "from governance_core import TestRunner"

def _already_imported(src):
    return "from governance_core" in src or "import governance_core" in src


def _insert_import(src: str, import_line: str) -> str:
    """Insert import_line after the last 'import ...' / 'from ... import ...' line."""
    lines = src.splitlines(keepends=True)
    last_import = -1
    for i, ln in enumerate(lines):
        if re.match(r"^(import |from )\S", ln):
            last_import = i
    if last_import == -1:
        lines.insert(0, import_line + "\n")
    else:
        lines.insert(last_import + 1, import_line + "\n")
    return "".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Remove inline helper definitions
# ─────────────────────────────────────────────────────────────────────────────

# Matches a top-level def _sf / _safe_float / _c01 / _clamp01 block,
# including its docstring and body.  Stops at the next top-level def/class/
# assignment that doesn't start with spaces.
_HELPER_PAT = re.compile(
    r"\n\ndef (?:_safe_float|_sf|_clamp01|_c01)\([^)]*\)[^:]*:.*?(?=\n\n(?:def |class |[A-Z_])|\Z)",
    re.DOTALL,
)


def _remove_inline_helpers(src: str) -> str:
    """Strip _sf, _safe_float, _c01, _clamp01 function definitions."""
    return _HELPER_PAT.sub("", src)


def _rename_calls(src: str) -> str:
    """Normalise call-sites to use the short names _sf and _c01."""
    src = re.sub(r"\b_safe_float\(", "_sf(", src)
    src = re.sub(r"\b_clamp01\(", "_c01(", src)
    return src


# ─────────────────────────────────────────────────────────────────────────────
# Replace _run_tests boilerplate with TestRunner
# ─────────────────────────────────────────────────────────────────────────────

# Matches the counter + closure block:
#   passed = 0
#   failed = 0
#
#   def ok(...)
#       nonlocal passed, failed
#       ...
#
# (Some files have "passed = failed = 0" on one line.)

_COUNTER_BLOCK_VERBOSE = re.compile(
    r"    (passed\s*=\s*failed\s*=\s*0|passed\s*=\s*0\s*\n\s*failed\s*=\s*0)"
    r".*?"                           # anything up to the end of the ok() body
    r"(?=\n\n    (?:print|#|\w))",   # stop at next statement inside _run_tests
    re.DOTALL,
)

# The ok() closure itself (verbose variant)
_OK_CLOSURE_V = re.compile(
    r"\n\n    def ok\(label: str, cond(?:ition)?: bool\) -> None:\s*"
    r"nonlocal passed, failed\s*"
    r"if cond(?:ition)?:\s*"
    r"passed \+= 1\s*"
    r'print\(f"  PASS.*?"\)\s*'
    r"else:\s*"
    r"failed \+= 1\s*"
    r'print\(f"  FAIL.*?"\)',
    re.DOTALL,
)

# The ok() closure itself (silent variant — no PASS print)
_OK_CLOSURE_S = re.compile(
    r"\n\n    def ok\(\w+: str, \w+: bool\) -> None:\s*"
    r"nonlocal passed, failed\s*"
    r"if \w+:\s*"
    r"passed \+= 1\s*"
    r"else:\s*"
    r"failed \+= 1\s*"
    r'print\(f"  FAIL:.*?"\)',
    re.DOTALL,
)

# The summary block at the end (both variants)
_SUMMARY_V = re.compile(
    r'\n    print\(\)\s*\n    print\(SEP\)\s*\n    print\(f"Results: \{passed\} passed, \{failed\} failed out of \{passed\+failed\} tests"\)\s*\n    if failed == 0:\s*\n        print\("ALL TESTS PASSED"\)\s*\n    else:\s*\n        print\(f"\*\*\* \{failed\} FAILURE\(S\) \*\*\*"\)\s*\n    print\(\)',
    re.DOTALL,
)

# The SEP = "=" * 60 inside _run_tests  (some files define it locally)
_LOCAL_SEP = re.compile(r"\n    SEP = \"=\" \* 60\n")

# Opening print(SEP) / print("suite name") / print(SEP) block
_OPEN_BANNER = re.compile(
    r'\n    print\(SEP\)\n    print\("([^"]+)"\)\n    print\(SEP\)',
)

_OPEN_BANNER2 = re.compile(
    r'\n    print\(SEP\)\n    print\(f?"([^"]+)"\)\n    print\(SEP\)',
)


def _tr_var_name(src: str) -> str:
    """Return 'tr' (always — consistent naming)."""
    return "tr"


def _patch_run_tests_verbose(src: str, suite_name: str) -> str:
    """
    Replace the verbose _run_tests boilerplate with TestRunner calls.
    Handles the common structure of the 8 recent infra files.
    """
    # 1. Remove local SEP definition
    src = _LOCAL_SEP.sub("\n", src)

    # 2. Replace opening banner with tr.header()
    def _repl_banner(m):
        return f"\n    tr = TestRunner({m.group(1)!r})\n    tr.header()"
    src = _OPEN_BANNER.sub(_repl_banner, src, count=1)
    src = _OPEN_BANNER2.sub(_repl_banner, src, count=1)

    # 3. Remove "passed = 0 / failed = 0" lines
    src = re.sub(r"    passed\s*=\s*failed\s*=\s*0\n", "", src)
    src = re.sub(r"    passed\s*=\s*0\n\s*    failed\s*=\s*0\n", "", src)

    # 4. Remove the ok() closure (verbose variant)
    src = _OK_CLOSURE_V.sub("", src)

    # 5. Replace "print(f"\n--- {name} ---")" with tr.section(name)
    src = re.sub(
        r'    print\(f"\\n--- (.*?) ---"\)',
        r"    tr.section(\1)",
        src,
    )
    # Also handle print(f"\n--- name ---") with literal text
    src = re.sub(
        r'    print\("\\n--- (.*?) ---"\)',
        r'    tr.section("\1")',
        src,
    )

    # 6. Replace ok( calls
    src = re.sub(r"\bok\(", "tr.ok(", src)

    # 7. Replace summary block with tr.summary()
    # Try the known pattern
    src = _SUMMARY_V.sub("\n    tr.summary()", src)

    # Fallback: match any trailing "print Results / if failed / print()" block
    src = re.sub(
        r'\n    print\(\)\s*\n    print\((?:SEP|"[=]+")\)\s*\n    print\(f"Results:.*?\n    print\(\)\s*(?=\n\n|\Z)',
        "\n    tr.summary()\n",
        src,
        flags=re.DOTALL,
    )

    return src


def _patch_run_tests_silent(src: str, suite_name: str) -> str:
    """
    Replace the silent _run_tests boilerplate (FAIL-only) with TestRunner(verbose=False).
    Used for older modules that don't print PASS lines.
    """
    SEP62 = re.compile(r'    SEP = "=" \* 62\n')
    src = SEP62.sub("\n", src)
    src = _LOCAL_SEP.sub("\n", src)

    # Opening banner (may use SEP or literal ===...)
    def _repl_banner(m):
        return f"\n    tr = TestRunner({m.group(1)!r}, verbose=False)\n    tr.header()"

    src = re.sub(
        r'\n    print\("=" \* (?:60|62)\)\s*\n    print\("([^"]+)"\)\s*\n    print\("=" \* (?:60|62)\)',
        _repl_banner,
        src,
        count=1,
    )

    # Remove counter lines
    src = re.sub(r"    passed\s*=\s*failed\s*=\s*0\n", "", src)
    src = re.sub(r"    passed\s*=\s*0\n\s*    failed\s*=\s*0\n", "", src)

    # Remove the silent ok() closure
    src = _OK_CLOSURE_S.sub("", src)

    # Also handle slightly different signatures
    src = re.sub(
        r"\n\n    def ok\(\w+: str, \w+: bool\) -> None:\s*"
        r"nonlocal passed, failed\s*"
        r"if \w+:\s*passed \+= 1\s*"
        r"else:\s*failed \+= 1\s*"
        r'print\(f"  FAIL:.*?"\)',
        "",
        src,
        flags=re.DOTALL,
    )

    # print("\n--- ... ---") → tr.section(...)
    src = re.sub(
        r'    print\(f"\\n--- (.*?) ---"\)',
        r"    tr.section(\1)",
        src,
    )
    src = re.sub(
        r'    print\("\\n--- (.*?) ---"\)',
        r'    tr.section("\1")',
        src,
    )

    # ok( → tr.ok(
    src = re.sub(r"\bok\(", "tr.ok(", src)

    # Summary block → tr.summary()
    src = re.sub(
        r'    print\(\)\s*print\(f"Results: \{passed\} passed.*?print\(\)',
        "    tr.summary()",
        src,
        flags=re.DOTALL,
    )
    src = re.sub(
        r'    print\(\)\s*\n    print\("=" \* (?:60|62)\)\s*\n    print\(f"Results: \{passed\}.*?\n    print\(\)',
        "\n    tr.summary()",
        src,
        flags=re.DOTALL,
    )

    return src


# ─────────────────────────────────────────────────────────────────────────────
# File groups
# ─────────────────────────────────────────────────────────────────────────────

# Group A: have inline _sf/_c01 AND verbose TestRunner
GROUP_A = [
    ("axiom_infra.py",                   "axiom_infra  —  unit tests",               True),
    ("determinism_infra.py",             "determinism_infra  —  unit tests",          True),
    ("divergence_convergence_infra.py",  "divergence_convergence_infra  —  unit tests", True),
    ("faith_infra.py",                   "faith_infra  —  unit tests",               True),
    ("natural_guardrail_infra.py",       "natural_guardrail_infra  —  unit tests",   True),
    ("ontology_compression_infra.py",    "ontology_compression_infra  —  unit tests",True),
    ("quantum_ontology_engine.py",       "quantum_ontology_engine  —  unit tests",   True),
    # dimensional_governor has only _c01, no _sf, no verbose ok
    ("dimensional_governor.py",          "",                                          False),
]

# Group B: verbose TestRunner, no inline helpers
GROUP_B = [
    ("agi_triage_infra.py",                  "agi_triage_infra  —  unit tests"),
    ("reconciliation_infra.py",              "reconciliation_infra  —  unit tests"),
    ("digital_generation_detector_infra.py", "digital_generation_detector_infra  —  unit tests"),
    ("incalculable_infra.py",                "incalculable_infra  —  unit tests"),
    ("math_break_infra.py",                  "math_break_infra  —  unit tests"),
    ("meta_omega7_infra.py",                 "meta_omega7_infra  —  unit tests"),
    ("meta_singular_math_ontology_infra.py", "meta_singular_math_ontology_infra  —  unit tests"),
    ("poly_federation_mesh_infra.py",        "poly_federation_mesh_infra  —  unit tests"),
    ("resonance_coherence_infra.py",         "resonance_coherence_infra  —  unit tests"),
    ("singularity_reemergence_infra.py",     "singularity_reemergence_infra  —  unit tests"),
    ("stress_edge_case_infra.py",            "stress_edge_case_infra  —  unit tests"),
    ("stress_test_infra.py",                 "stress_test_infra  —  unit tests"),
]

# Group C: silent ok (FAIL-only), no helpers
GROUP_C = [
    ("pattern_analytic_infra.py",        "pattern_analytic_infra.py — Test Suite"),
    ("pattern_drift_infra.py",           "pattern_drift_infra.py — Test Suite"),
    ("pattern_trap_infra.py",            "pattern_trap_infra.py — Test Suite"),
    ("recursive_biology_federation.py",  "recursive_biology_federation.py — Test Suite"),
    ("recursive_emergence_federation.py","recursive_emergence_federation.py — Test Suite"),
    ("recursive_sociology_federation.py","recursive_sociology_federation.py — Test Suite"),
    ("recursive_sos_federation.py",      "recursive_sos_federation.py — Test Suite"),
    ("swarm_mesh_federation.py",         "swarm_mesh_federation.py — Test Suite"),
    ("em_signal_mixing_infra.py",        "em_signal_mixing_infra.py — Test Suite"),
    ("em_signal_mixing_detector_infra.py","em_signal_mixing_detector_infra.py — Test Suite"),
    ("bio_signal_infra.py",              "bio_signal_infra.py — Test Suite"),
    ("eye_movement_infra.py",            "eye_movement_infra.py — Test Suite"),
    ("logic_signal_infra.py",            "logic_signal_infra.py — Test Suite"),
    ("llm_ui_infra.py",                  "llm_ui_infra.py — Test Suite"),
    ("movement_infra.py",                "movement_infra.py — Test Suite"),
    ("predictive_recursion_infra.py",    "predictive_recursion_infra.py — Test Suite"),
    ("sound_infra.py",                   "sound_infra.py — Test Suite"),
    ("time_infra.py",                    "time_infra.py — Test Suite"),
    ("visual_infra.py",                  "visual_infra.py — Test Suite"),
    ("pr_topology.py",                   "pr_topology.py — Test Suite"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Apply patches
# ─────────────────────────────────────────────────────────────────────────────

def patch_group_a():
    print("\n=== Group A: remove inline helpers + wire TestRunner ===")
    for fname, suite_name, has_verbose in GROUP_A:
        if not os.path.exists(fname):
            print(f"  SKIP (not found): {fname}")
            continue
        src = read(fname)
        if _already_imported(src):
            print(f"  SKIP (already done): {fname}")
            continue

        # Remove inline helper definitions
        src = _remove_inline_helpers(src)
        src = _rename_calls(src)

        # Wire TestRunner (for verbose files)
        if has_verbose and suite_name:
            src = _patch_run_tests_verbose(src, suite_name)
            import_line = CORE_IMPORT_SF
        elif fname == "dimensional_governor.py":
            # Only has _c01, no test runner update
            import_line = CORE_IMPORT_C01
        else:
            import_line = CORE_IMPORT_SF

        src = _insert_import(src, import_line)
        write(fname, src)


def patch_group_b():
    print("\n=== Group B: verbose TestRunner only ===")
    for fname, suite_name in GROUP_B:
        if not os.path.exists(fname):
            print(f"  SKIP (not found): {fname}")
            continue
        src = read(fname)
        if _already_imported(src):
            print(f"  SKIP (already done): {fname}")
            continue

        src = _patch_run_tests_verbose(src, suite_name)
        src = _insert_import(src, CORE_IMPORT_TR)
        write(fname, src)


def patch_group_c():
    print("\n=== Group C: silent TestRunner (verbose=False) ===")
    for fname, suite_name in GROUP_C:
        if not os.path.exists(fname):
            print(f"  SKIP (not found): {fname}")
            continue
        src = read(fname)
        if _already_imported(src):
            print(f"  SKIP (already done): {fname}")
            continue

        src = _patch_run_tests_silent(src, suite_name)
        src = _insert_import(src, CORE_IMPORT_TR)
        write(fname, src)


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    patch_group_a()
    patch_group_b()
    patch_group_c()
    print("\nDone. Run: python -m pytest *.py  or  for f in *.py; do python $f; done")
