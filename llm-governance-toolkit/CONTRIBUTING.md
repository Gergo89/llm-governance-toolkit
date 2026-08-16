# Contributing

Contributions should preserve the toolkit's core properties: narrow scope, deterministic behavior,
fail-closed governance, explicit limitations, and reproducible evidence.

## Development setup

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt
```

## Validation

Run the fast PR checks while developing:

```bash
ruff check .
pytest -m "not stress"
python -m build
```

Run the exhaustive validation before changing an invariant, threshold, or governance decision:

```bash
python stress_test.py
python cage_stress_test.py
```

The exhaustive suite is also run on `main`, nightly, and on manual dispatch. Its JSON and figure
outputs are uploaded as GitHub Actions artifacts with a reproducibility manifest.

## Pull requests

- Explain the governed invariant and the failure mode the change addresses.
- Add a deterministic regression test for behavior changes.
- Keep generated benchmark outputs out of the source diff unless intentionally updating a
  publication baseline.
- Call out compatibility changes and new dependencies explicitly.
- Do not weaken a fail-closed decision without explaining the new authority boundary.
