#!/usr/bin/env python3
"""
severity_taxonomy_casestudy.py — the taxonomy engine pointed at a REAL taxonomy, not a toy one.

The case: an organization ingests logs from many systems and wants ONE normalized severity axis so
alerting and routing behave consistently. The severity levels of the source systems are REAL and
documented, and they do not agree:

  * syslog (RFC 5424, severities 0–7): Emergency, Alert, Critical, Error, Warning, Notice,
    Informational, Debug.
  * Python `logging`: CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET (FATAL/WARN are aliases).
  * Google Cloud Logging (LogSeverity): DEFAULT, DEBUG, INFO, NOTICE, WARNING, ERROR, CRITICAL,
    ALERT, EMERGENCY.

We declare a reasonable canonical axis (FATAL / ERROR / WARN / INFO / DEBUG / TRACE, default
UNMAPPED), map every real source level into it, and run `taxonomy_builder.validate()` over the union
of real levels. The validator surfaces genuine, structural problems with the mapping — the same
coverage / exclusivity / dead-entry issues a tokenizer's vocabulary faces — that would otherwise hide
inside ad-hoc mapping code and cause real alerting bugs.

Deterministic, self-testing. Reuses taxonomy_builder. Standard library only.
Run:  python severity_taxonomy_casestudy.py
"""

from __future__ import annotations
import os, sys
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import taxonomy_builder as tb            # noqa: E402


# --- the REAL source level sets (documented), each level tagged with its source ---------
def source_levels() -> List[Dict[str, str]]:
    syslog = ["Emergency", "Alert", "Critical", "Error", "Warning", "Notice", "Informational", "Debug"]
    python = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"]
    gcp = ["DEFAULT", "DEBUG", "INFO", "NOTICE", "WARNING", "ERROR", "CRITICAL", "ALERT", "EMERGENCY"]
    items = []
    for name in syslog:
        items.append({"source": "syslog", "name": name})
    for name in python:
        items.append({"source": "python", "name": name})
    for name in gcp:
        items.append({"source": "gcp", "name": name})
    return items


# --- a reasonable canonical severity axis an org would normalize to ----------------------
def canonical_severity() -> tb.Taxonomy:
    def U(item): return item["name"].upper()
    axis = tb.Axis("severity", (
        tb.Category("FATAL", lambda i: U(i) in {"EMERGENCY", "ALERT", "CRITICAL", "FATAL"}),
        tb.Category("ERROR", lambda i: U(i) in {"ERROR", "ERR"}),
        # NOTICE is deliberately allowed to match WARN here AND INFO below — the real ambiguity:
        tb.Category("WARN",  lambda i: U(i) in {"WARNING", "WARN", "NOTICE"}),
        tb.Category("INFO",  lambda i: U(i) in {"INFORMATIONAL", "INFO", "NOTICE"}),
        tb.Category("DEBUG", lambda i: U(i) in {"DEBUG"}),
        tb.Category("TRACE", lambda i: U(i) in {"TRACE"}),        # canonical has TRACE; no source emits it
    ), default="UNMAPPED")                                        # DEFAULT / NOTSET land here
    return tb.Taxonomy("canonical_severity", (axis,))


def _iid(i): return f"{i['source']}:{i['name']}"


def granularity_collapse(tax, items):
    """How many distinct source levels collapse into each canonical level (information loss)."""
    buckets: Dict[str, List[str]] = {}
    for it in items:
        c = tb.classify(tax, it)["severity"]
        buckets.setdefault(c, []).append(_iid(it))
    return buckets


def _self_test() -> None:
    tax, items = canonical_severity(), source_levels()
    rep = tb.validate(tax, items, item_id=_iid)
    ax = rep.axes[0]

    # OVERLAP: NOTICE (syslog + gcp) matches WARN and INFO — the real ambiguity
    ov = {iid: cats for iid, cats in ax.overlaps}
    assert ov.get("syslog:Notice") == ("WARN", "INFO")
    assert ov.get("gcp:NOTICE") == ("WARN", "INFO")
    assert len(ax.overlaps) == 2

    # GAPS: 'no severity' levels have no canonical home
    assert set(ax.gaps) == {"python:NOTSET", "gcp:DEFAULT"}

    # DEAD ENTRY: TRACE is in the canonical schema but no source emits it
    assert ax.empty_categories == ("TRACE",)

    # coverage = 21/23 real levels mapped
    assert abs(ax.coverage - 21/23) < 1e-9

    # greedy first-match resolves NOTICE to WARN silently (validate is what exposes the ambiguity)
    assert tb.classify(tax, {"source": "gcp", "name": "NOTICE"})["severity"] == "WARN"

    # granularity collapse: FATAL absorbs 7 distinct source levels (Emergency/Alert/Critical ×2+CRITICAL)
    coll = granularity_collapse(tax, items)
    assert len(coll["FATAL"]) == 7

    assert tb.validate(tax, items, _iid).render() == tb.validate(tax, items, _iid).render()
    print("self-test passed")


if __name__ == "__main__":
    _self_test()
    tax, items = canonical_severity(), source_levels()
    print("\n=== CASE STUDY: normalizing log severity across syslog / Python / Google Cloud ===\n")
    print("  mapping each real source level to the canonical axis (greedy first-match):\n")
    for it in items:
        print(f"    {_iid(it):22} -> {tb.classify(tax, it)['severity']}")

    print("\n  validate() over the union of real levels:\n")
    print(tb.validate(tax, items, item_id=_iid).render())

    coll = granularity_collapse(tax, items)
    print("\n  granularity collapse (distinct source levels absorbed per canonical bucket):")
    for c in ("FATAL", "ERROR", "WARN", "INFO", "DEBUG", "UNMAPPED"):
        if c in coll:
            print(f"    {c:9} <- {len(coll[c])}: {', '.join(coll[c])}")

    print("\n  what the four findings mean operationally:")
    print("   • OVERLAP (Notice→WARN&INFO): the same level routes/pages differently depending on")
    print("     greedy order — a silent inconsistency across services. Decide NOTICE's mapping explicitly.")
    print("   • GAPS (NOTSET, DEFAULT): 'no severity' logs fall to UNMAPPED and can be silently dropped")
    print("     or mis-routed. Add an explicit rule (usually → INFO or a quarantine bucket).")
    print("   • DEAD ENTRY (TRACE): the canonical schema promises a level nothing populates — false")
    print("     coverage. Drop it, or wire a source that actually emits TRACE.")
    print("   • GRANULARITY COLLAPSE (FATAL <- 7): Emergency/Alert/Critical distinctions are lost, so")
    print("     you cannot page differently on 'system unusable' vs 'critical' after normalization.")
