# Generated validation evidence

Stress-test JSON and figures are generated during the scheduled or manually dispatched
`Stress Tests` workflow. GitHub Actions uploads them as a retained artifact together with
`manifest.json`, which records the commit, Python version, platform, and generation time.

Generated files in this directory are intentionally ignored by Git. The checked-in figures and
result snapshots elsewhere in the repository remain publication baselines; fresh CI evidence is
kept separate so routine validation does not create source diffs.
