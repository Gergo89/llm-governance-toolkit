# Case Study — Auditing a Real Taxonomy: Normalizing Log Severity

*The taxonomy engine (`taxonomy_builder`) pointed at a real, documented classification problem —
unifying log-severity levels across three production logging systems — and the concrete defects its
`validate()` surfaces in a mapping that would otherwise look fine. Runnable:
`severity_taxonomy_casestudy.py`.*

---

## Context

Any organization running more than one system ingests logs whose **severity levels don't agree**.
To alert, route, and page consistently, those levels must be normalized onto one canonical axis. That
normalization is almost always written as ad-hoc mapping code buried in a log pipeline — and bugs in
it (a level that routes two ways, a level that silently vanishes, a promised level nothing emits) are
invisible until they cause a missed page or a dropped error. A normalization *is* a taxonomy, so it
can be declared and audited instead of hand-wired and hoped over.

## The real inputs (documented)

Three real, published severity schemes, which genuinely disagree in granularity and naming:

- **syslog** (RFC 5424, severities 0–7): Emergency, Alert, Critical, Error, Warning, Notice,
  Informational, Debug.
- **Python `logging`**: CRITICAL, ERROR, WARNING, INFO, DEBUG, NOTSET (FATAL/WARN are aliases).
- **Google Cloud Logging** (`LogSeverity`): DEFAULT, DEBUG, INFO, NOTICE, WARNING, ERROR, CRITICAL,
  ALERT, EMERGENCY.

## Method

A reasonable canonical axis an org would normalize to — **FATAL / ERROR / WARN / INFO / DEBUG /
TRACE**, default **UNMAPPED** — is declared as a taxonomy, every one of the 23 real source levels is
mapped into it, and `validate()` audits the result for the three ways a partition fails: coverage
gaps, category overlaps, and dead (empty) categories.

## Findings

Over the 23 real levels, `validate()` reports **91% coverage** and three structural defects, plus a
fourth the run computes alongside:

| Finding | What `validate()` reported | Operational consequence |
|---|---|---|
| **Overlap** | `syslog:Notice` and `gcp:NOTICE` each match **WARN and INFO** | The same level routes/pages **differently depending on greedy order** — a silent inconsistency across services. NOTICE genuinely sits between INFO and WARNING; the mapping must decide, not leave it to rule order. |
| **Coverage gaps** | `python:NOTSET` and `gcp:DEFAULT` fall through to **UNMAPPED** | "No-severity" logs land in a default bucket where they can be **silently dropped or mis-routed**. Needs an explicit rule (→ INFO, or a quarantine bucket). |
| **Dead entry** | canonical **TRACE** is never populated | The schema **promises a level nothing emits** — false coverage. TRACE exists in Log4j/SLF4J/OpenTelemetry but not in these three sources; drop it or wire a source that emits it. |
| **Granularity collapse** | **FATAL absorbs 7** distinct source levels (Emergency, Alert, Critical ×2, and more) | After normalization you **cannot page differently on "system unusable" (Emergency) vs "critical"** — a real loss of actionable distinction, invisible in the mapping code. |

Note the mechanism on the overlap: `classify()` returns a single answer (`NOTICE → WARN`) by
first-match, exactly the way a greedy resolver silently picks one branch. `validate()` is what makes
the *hidden* second match visible — the defect you would otherwise ship.

## Interpretation

None of these are contrived; each is a direct consequence of three real schemes having different
granularities and one genuinely ambiguous level (NOTICE). The value of running the taxonomy validator
is that the normalization stops being trusted code and becomes an **audited artifact**: the ambiguity
is named and forced to a decision, the "no severity" case is handled on purpose, the vacuous level is
removed, and the granularity loss is made explicit so someone can decide whether Emergency-vs-Critical
matters for paging. This is the same coverage/exclusivity/dead-entry hygiene a tokenizer's vocabulary
needs — here applied to a schema an on-call engineer actually depends on.

## Honest scope

Validation is over the **declared sources**: it proves the mapping is complete, exclusive, and
non-vacuous *for these three schemes' levels*, not for every conceivable log source. The canonical
axis and mapping are one reasonable choice, stated and auditable, not the only correct one — which is
exactly the point: the tool doesn't pick the normalization for you, it makes the one you picked
inspectable. Deterministic, self-testing, stdlib-only.

## Lessons

A classification schema is infrastructure, and un-audited schema infrastructure fails the way
un-audited code does — quietly, at the boundary. Declaring the mapping and running coverage /
exclusivity / dead-entry checks *before* building alerting on top of it converts four latent
production bugs (inconsistent NOTICE routing, dropped no-severity logs, a phantom TRACE level, and an
un-pageable FATAL bucket) into four explicit, fixable design decisions.
