#!/usr/bin/env python3
"""
Version management utility for AGI project.

Usage:
    python scripts/manage-version.py bump <major|minor|patch>
    python scripts/manage-version.py set <version>
    python scripts/manage-version.py current
"""

import re
import sys
from pathlib import Path
from typing import Tuple


def parse_version(version_str: str) -> Tuple[int, int, int]:
    """Parse semantic version string."""
    parts = version_str.split('.')
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {version_str}")
    return tuple(int(p) for p in parts)


def bump_version(current: str, bump_type: str) -> str:
    """Bump version based on type: major, minor, or patch."""
    major, minor, patch = parse_version(current)
    
    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Unknown bump type: {bump_type}")


def get_current_version() -> str:
    """Get current version from pyproject.toml."""
    pyproject = Path("llm-governance-toolkit/pyproject.toml")
    if not pyproject.exists():
        raise FileNotFoundError(f"pyproject.toml not found at {pyproject}")
    
    content = pyproject.read_text()
    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    if not match:
        raise ValueError("Version not found in pyproject.toml")
    return match.group(1)


def update_version_in_file(file_path: Path, old_version: str, new_version: str):
    """Update version string in a file."""
    if not file_path.exists():
        print(f"Warning: {file_path} not found, skipping")
        return
    
    content = file_path.read_text()
    updated = content.replace(
        f'version = "{old_version}"',
        f'version = "{new_version}"'
    )
    
    if updated != content:
        file_path.write_text(updated)
        print(f"Updated {file_path}")
    else:
        print(f"No version string found in {file_path}")


def update_version(new_version: str):
    """Update version in all relevant files."""
    current = get_current_version()
    
    if new_version == current:
        print(f"Version is already {current}")
        return
    
    files_to_update = [
        Path("llm-governance-toolkit/pyproject.toml"),
    ]
    
    for file_path in files_to_update:
        update_version_in_file(file_path, current, new_version)
    
    print(f"Version bumped: {current} -> {new_version}")
    print("\nNext steps:")
    print(f"1. Review changes and update CHANGELOG.md")
    print(f"2. Commit: git commit -am 'chore: bump version to {new_version}'")
    print(f"3. Tag: git tag -a v{new_version} -m 'Release {new_version}'")
    print(f"4. Push: git push && git push --tags")
    print(f"5. GitHub will automatically publish to PyPI")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    command = sys.argv[1]
    
    try:
        if command == "current":
            print(f"Current version: {get_current_version()}")
        elif command == "bump" and len(sys.argv) == 3:
            current = get_current_version()
            new_version = bump_version(current, sys.argv[2])
            update_version(new_version)
        elif command == "set" and len(sys.argv) == 3:
            update_version(sys.argv[2])
        else:
            print(__doc__)
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
