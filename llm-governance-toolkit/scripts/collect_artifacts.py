#!/usr/bin/env python3
"""Collect generated stress evidence and attach reproducibility metadata."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATED = (
    "stress_results.json",
    "cage_stress_results.json",
    "decoupling_monitor_fig.png",
    "ground_truth_auditor_fig.png",
    "optimal_timing_fig.png",
    "tools/gene_shift_fig.png",
    "tools/telemetry_infra_fig.png",
    "tools/temporal_telemetry_fig.png",
)


def _git_sha() -> str | None:
    github_sha = os.environ.get("GITHUB_SHA")
    if github_sha:
        return github_sha
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def collect(output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    collected = []
    for relative in GENERATED:
        source = ROOT / relative
        if not source.is_file():
            continue
        destination = output_dir / source.name
        shutil.copy2(source, destination)
        collected.append(destination.name)

    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "commit": _git_sha(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "randomness": "seeded by the stress harness; see stress_test.py",
        "workflow_outcomes": {
            "main_stress": os.environ.get("MAIN_STRESS_OUTCOME"),
            "cage_stress": os.environ.get("CAGE_STRESS_OUTCOME"),
        },
        "files": sorted(collected),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return collected


if __name__ == "__main__":
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "artifacts"
    files = collect(destination.resolve())
    print(f"collected {len(files)} evidence files in {destination}")
