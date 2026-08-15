# Mapping Integrity: a governance layer for ontology mappings

*A short design note. Ontology **matching** — producing mappings between vocabularies — is a
mature field. What is under-governed is mapping **integrity**: whether a mapping is trustworthy,
and whether it still holds as the ontologies it connects evolve. This note specifies that
governance layer, built by reusing the existing toolkit unchanged, over the SSSOM standard. It
does not build another matcher.*

---

## The problem

Enterprises and knowledge bases run on mappings between overlapping vocabularies — SNOMED↔ICD,
supplier catalogs, industrial standards, internal schemas. The matchers that produce these
(the OAEI ecosystem; Euzenat & Shvaiko's *Ontology Matching*; LogMap, AML; increasingly LLM
matchers) are good and well-studied. The gap is downstream and quieter: **a wrong mapping
silently corrupts everything built on it**, and a *once-correct* mapping decays as both
ontologies change. Two failure modes, both invisible until damage is done:

1. **Overclaimed equivalence** — a mapping asserted as `skos:exactMatch` that is actually a
   lexical guess or an unaudited auto-alignment, adopted downstream as if it were verified.
2. **Mapping drift** — a genuinely-correct mapping whose source or target term is later
   refined, split, or **obsoleted** in a new ontology version, leaving the mapping dangling or
   subtly wrong while it keeps being used.

Neither is a matching problem; both are *integrity and evolution* problems — exactly the
proxy-vs-truth territory the toolkit targets.

## Scope and stance

- **Build on, don't reinvent.** Express everything over **SSSOM** (the Simple Standard for
  Sharing Ontological Mappings), whose records already carry the fields this layer needs —
  `predicate_id` (the SKOS relation), `mapping_justification` (SEMAPV: manual curation,
  lexical, logical, …), `confidence`, `author_id`. The layer *reads and enforces* those fields
  rather than inventing a format. It sits on top of whatever matcher produced the mappings.
- **It governs integrity, not matching.** It does not decide whether two terms mean the same
  thing; it grades how well-supported that claim is, stops it from self-certifying, and watches
  it over time.

## The layer (reuses the toolkit unchanged)

Each mapping is treated as a *claim* and run through four existing components:

| Component | On a mapping | Reads / enforces |
|---|---|---|
| `knowledge_maturity` | grades the mapping's evidentiary status, with critical gates | SSSOM `mapping_justification` + `confidence`: a *lexical* justification cannot be graded as high as *manual curation* or *logical reasoning*; quantity of string-matches can't buy past a missing human/logical check |
| non-self-approval (`soi_pipeline`) | a consequential mapping cannot certify itself | requires a distinct human `author_id`/reviewer sign-off before a mapping is **validated** (vs merely **adopted** as a working alignment); adoption ≠ validation |
| `goodhart_auditor` | audits mapping metadata for overclaim | flags a record asserting `exactMatch` whose justification is only `LexicalMatching` — a predicate that claims more than its backing checks |
| `decoupling_monitor` | **drift detection**: asserted equivalence (proxy) vs current domain reality (truth) across versions | alerts when a mapping's downstream behavior diverges from an independent check as the ontologies change |

### Obsoletion-driven drift (the evolution piece)

The strongest, most differentiated part reuses the obsoletion measurement from the REO/OBO
work. OBO-style ontologies mark terms obsolete (`owl:deprecated`, `obsolete` labels, often with
`replaced_by`/`consider`). On each new version, the layer checks every mapping's `subject_id`
and `object_id` against the latest release:

- **term obsoleted with `replaced_by`** → the mapping is *stale*; propose the repaired mapping to the replacement, route to human review (never auto-repair silently).
- **term obsoleted with no replacement** → the mapping is *dangling*; demote it below **validated** and flag for removal.
- **term split / re-scoped** → the equivalence relation may need to weaken (`exactMatch` → `broadMatch`/`narrowMatch`); flag for re-grading.

This makes "evolution" concrete and testable — ontology change and obsoletion driving mapping
decay — which is precisely where your prior obsoletion study already did the hard measurement.
(Deliberately: *evolution* here means versioning, obsoletion, and drift — a measurable
mechanism, not a generative framing.)

## Mapping status ladder

Combining the above, each mapping carries an explicit, machine-checkable status:

```
ASSERTED  <  HEURISTIC  <  REVIEWED  <  VALIDATED  <  CANONICAL
```

`VALIDATED` is unreachable while the justification is only lexical, while a metadata field
overclaims, while no distinct human has signed, or while either endpoint is obsoleted. A new
ontology release can *demote* a previously-validated mapping — the drift signal, made a
first-class status change rather than an invisible rot.

## Honest limits

- **It needs an independent notion of "really equivalent."** Drift detection is only as good as
  the independent check of true correspondence — the same binding constraint as everywhere: you
  cannot detect a mapping decoupling from reality without a second, un-gamed measure of reality.
  Obsoletion is a *free* independent signal (it comes from the ontology maintainers, not the
  mapping), which is why it's the strongest lever here.
- **It governs integrity, not correctness.** A validated mapping can still be wrong; human
  domain judgment stays load-bearing. The layer guarantees a *weak* or *stale* mapping can't
  pass as verified, not that a passing one is true.
- **It is a layer, not a matcher.** It presupposes SSSOM mappings from some source; it adds
  grading, non-self-approval, overclaim auditing, and drift/obsoletion monitoring on top.
- **Engage the field.** SSSOM, OAEI, and the ontology-evolution literature already exist; the
  contribution is the *governance-and-drift* layer and its reuse of a self-testing toolkit, not
  a new alignment method.

## Where it sits

Alongside the other governance pieces, this is the same pattern applied to a new artifact: a
mapping is a claim with evidence that shouldn't self-certify and can decouple from reality over
time. It reuses `knowledge_maturity`, `soi_pipeline` (non-self-approval), `goodhart_auditor`,
and `decoupling_monitor` unchanged, plus the obsoletion method from the REO study — no new core
machinery, one honest new application.

## Applicability and exclusions

This layer is **not safety-critical software** and must not sit on the critical path of any life-
or mission-critical control function. It carries none of the assurance evidence such roles
require: it is not developed or verified to **DO-178C** (up to Design Assurance Level A) or
**DO-254** for airborne systems, to **IEC 61508** Safety Integrity Levels (with their quantified
dangerous-failure targets — SIL 4 ≈ 10⁻⁴–10⁻⁵ probability of failure on demand), to **IEC 61513 /
IEC 60880 / IEEE 7-4.3.2** for nuclear **Class 1E** instrumentation and control, or to
**MIL-STD-882** system-safety practice; it provides no formal proof, no hardware fault tolerance,
no redundancy or diversity, no real-time determinism, and no independent V&V, and it governs
mapping *metadata* only — it issues no control action at all, so it cannot be, and must not be
mistaken for, an element of a safety function. Its legitimate role in nuclear, aerospace, and
defense contexts is confined to the **non-safety-critical AI and analytical layer** — grading and
drift-monitoring the vocabularies and ontology mappings that feed decision *support*, with
evidence-maturity ordering, metric-gaming audits, and non-self-approval of analyses — always
advisory, off the critical path, with certified systems and human authorities retaining control.
Where its ethos aligns with meaningful-human-control principles (e.g. **DoD Directive 3000.09**),
that is alignment in intent, not certification of fitness: a mapping it marks `VALIDATED` is an
integrity grade, **not** clearance for use in flight-critical, reactor-protection, or nuclear
command-and-control / weapons-release functions.

**Next step (optional):** a small self-testing stub — take a handful of SSSOM rows across two
ontology versions and show a `LexicalMatching`-justified `exactMatch` held at `HEURISTIC`, a
human-signed one reaching `VALIDATED`, and a validated mapping *demoted* when its target term is
obsoleted in the new release. Mirrors the benefits and eval-integrity demonstrators.
