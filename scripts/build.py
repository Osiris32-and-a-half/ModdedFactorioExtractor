#!/usr/bin/env python3
"""Build Factorio-compatible ZIPs for supported game versions."""

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


ROOT = Path(__file__).resolve().parents[1]
MOD_DIRECTORY = ROOT / "archipelago-extractor"
BUILD_DIRECTORY = ROOT / "build"
TARGETS = ("2.0", "2.1")
VERSION_PATTERN = re.compile(r"^\d+\.\d+\.(\d+)$")


def build_target(target: str) -> Path:
    info_path = MOD_DIRECTORY / "info.json"
    with info_path.open(encoding="utf-8") as info_file:
        info: Dict[str, Any] = json.load(info_file)

    name = info.get("name")
    source_version = info.get("version")
    if not isinstance(name, str) or not isinstance(source_version, str):
        raise ValueError(f"{info_path} must define string name and version fields")

    version_match = VERSION_PATTERN.fullmatch(source_version)
    if version_match is None:
        raise ValueError(
            f"Unsupported mod version {source_version!r}; expected MAJOR.MINOR.PATCH"
        )

    mod_version = f"{target}.{version_match.group(1)}"
    info["version"] = mod_version
    info["factorio_version"] = target
    archive_path = BUILD_DIRECTORY / f"{name}_{mod_version}.zip"
    BUILD_DIRECTORY.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(
        archive_path, mode="w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for source_path in sorted(MOD_DIRECTORY.rglob("*")):
            if not source_path.is_file():
                continue
            archive_name = source_path.relative_to(MOD_DIRECTORY).as_posix()
            if archive_name == "info.json":
                archive.writestr(
                    archive_name,
                    json.dumps(info, indent=4) + "\n",
                )
            else:
                archive.write(source_path, archive_name)

    return archive_path


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Factorio mod ZIPs for Factorio 2.0 and 2.1."
    )
    parser.add_argument(
        "targets",
        nargs="*",
        choices=TARGETS,
        metavar="TARGET",
        help="Target version(s): 2.0 and/or 2.1. Defaults to both.",
    )
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    targets = args.targets or list(TARGETS)
    try:
        for target in dict.fromkeys(targets):
            archive_path = build_target(target)
            print(archive_path.relative_to(ROOT))
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"Build failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
