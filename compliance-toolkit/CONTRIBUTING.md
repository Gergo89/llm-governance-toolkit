# Contributing

Contributions welcome, particularly regulatory corrections and control
mappings. Two rules do the heavy lifting.

## 1. Regulatory claims need sources

Any change to a date, an article number, an obligation or a jurisdiction must
add or update an entry in [`compliance/SOURCES.md`](compliance/SOURCES.md) with
a link. Prefer primary sources — Official Journal, NIST, the regulator itself.
Law-firm analysis is acceptable where it is the clearest available summary, but
name the firm and the date.

If you cannot source it, mark it as interpretation rather than fact.

## 2. Control changes need tests

Adding or changing a control in
`src/llm_governance/resources/controls.yaml` requires:

- references for all three frameworks (`eu_ai_act`, `nist_ai_rmf`, `iso_42001`)
  — a test enforces this
- tier applicability that is monotonic: a control mandatory at `minimal` must
  also be mandatory at `limited` and `high` — also enforced by a test
- at least one concrete evidence artefact, not "documentation"

New policy rules in `policy.py` need a test for both the firing and the
non-firing case. A rule with no negative test tends to fire on everything.

## Development

```bash
pip install -e ".[dev]"
pytest -q
ruff check src tests
make crosswalks      # regenerate generated-crosswalk.md files
```

Generated crosswalks are not hand-edited. Change the control, regenerate.

## Style

**Documents.** Write for the person who has to act on it, not the person
auditing it. Prefer a concrete example over a definition. Say what to do, then
why. If a sentence could appear in any AI governance document ever written,
delete it.

**Code.** Standard library plus PyYAML and jsonschema. No new runtime
dependencies without a good reason — the toolkit is meant to install cleanly in
a locked-down enterprise environment. Keep it working offline.

**Templates.** Every blank is `{{PLACEHOLDER}}` in caps, and every placeholder
represents a real decision. Do not add placeholders for things that have an
obvious default.

## What this project is not

It is not legal advice, and pull requests that present it as such will be
rejected. It is not a conformity assessment tool. It is not a substitute for a
DPO, and it does not try to be exhaustive across jurisdictions — the US state
picture in particular moves faster than any repository can track.

## Reporting a problem

Wrong regulatory statements are the highest-priority bug class here, because
they are the ones that cause harm downstream. Open an issue with the incorrect
text, the correct position, and a source.
