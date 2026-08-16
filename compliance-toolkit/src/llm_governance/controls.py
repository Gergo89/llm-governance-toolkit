"""Loading and querying the control catalogue."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional

import yaml

from .models import Control, Tier

DEFAULT_CATALOGUE = Path(__file__).parent / "resources" / "controls.yaml"


class ControlCatalogue:
    """An indexed, immutable view over the control catalogue."""

    def __init__(self, controls: Iterable[Control], version: str = "unknown") -> None:
        self._controls: List[Control] = list(controls)
        self._by_id: Dict[str, Control] = {c.id: c for c in self._controls}
        if len(self._by_id) != len(self._controls):
            seen, dupes = set(), set()
            for c in self._controls:
                if c.id in seen:
                    dupes.add(c.id)
                seen.add(c.id)
            raise ValueError(f"duplicate control ids in catalogue: {', '.join(sorted(dupes))}")
        self.version = version

    # -- construction ------------------------------------------------------ #

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "ControlCatalogue":
        path = Path(path) if path else DEFAULT_CATALOGUE
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

        controls = []
        for entry in data.get("controls", []):
            controls.append(
                Control(
                    id=entry["id"],
                    title=entry["title"],
                    family=entry.get("family", "Uncategorised"),
                    statement=" ".join(entry.get("statement", "").split()),
                    tiers=list(entry.get("tiers", [])),
                    evidence=list(entry.get("evidence", [])),
                    references={k: list(v) for k, v in (entry.get("references") or {}).items()},
                    notes=" ".join(entry["notes"].split()) if entry.get("notes") else None,
                )
            )
        return cls(controls, version=str(data.get("version", "unknown")))

    # -- access ------------------------------------------------------------ #

    def __iter__(self):
        return iter(self._controls)

    def __len__(self) -> int:
        return len(self._controls)

    def __contains__(self, control_id: object) -> bool:
        return control_id in self._by_id

    def get(self, control_id: str) -> Optional[Control]:
        return self._by_id.get(control_id)

    def ids(self) -> List[str]:
        return [c.id for c in self._controls]

    def for_tier(self, tier: Tier) -> List[Control]:
        return [c for c in self._controls if c.applies_to(tier)]

    def families(self) -> List[str]:
        seen: List[str] = []
        for c in self._controls:
            if c.family not in seen:
                seen.append(c.family)
        return seen

    def by_framework(self, framework: str) -> Dict[str, List[Control]]:
        """Invert the catalogue: framework reference -> controls that satisfy it."""
        index: Dict[str, List[Control]] = {}
        for control in self._controls:
            for ref in control.references.get(framework, []):
                index.setdefault(ref, []).append(control)
        return dict(sorted(index.items()))
