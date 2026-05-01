#!/usr/bin/env python3
"""Copy a pipeline output file to a sibling approved-outputs directory.

Resolves a destination layout by taking the parent of the source file's
containing directory and appending "03_approved_outputs/" as a sibling of
that directory, preserving the original filename.

An explicit destination directory can be supplied with --dest-dir; this lets
multiple files from different source directories all land in the same place.

Usage:
    python file-copier.py --source-file path/to/file.csv
    python file-copier.py --source-file path/to/file.csv --dest-dir path/to/03_approved_outputs

Example (all files to a shared approved-outputs dir):
    python file-copier.py \\
        --source-file .../pl1A_canonical_population/00_sources/Grades-....csv
    # -> .../pl1A_canonical_population/03_approved_outputs/Grades-....csv

    python file-copier.py \\
        --source-file .../02_runs/02_join_key/submission_id_map.csv \\
        --dest-dir .../pl1A_canonical_population/03_approved_outputs
    # -> .../pl1A_canonical_population/03_approved_outputs/submission_id_map.csv
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Copy a file to a 03_approved_outputs directory that is a sibling "
            "of the file's containing directory."
        )
    )
    parser.add_argument(
        "--source-file",
        type=Path,
        required=True,
        help="Path to the file to copy.",
    )
    parser.add_argument(
        "--dest-dir",
        type=Path,
        required=False,
        default=None,
        help=(
            "Explicit destination directory. When omitted the destination is "
            "a 03_approved_outputs sibling of the source file's containing directory."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    src = args.source_file.resolve()

    if not src.exists():
        print(f"Error: source file not found: {src}", file=sys.stderr)
        sys.exit(1)

    # Destination: explicit dir if supplied, otherwise a 03_approved_outputs
    # sibling of the source file's containing directory.
    # e.g.  .../pl1A_canonical_population/00_sources/file.csv
    #   ->  .../pl1A_canonical_population/03_approved_outputs/file.csv
    dest_dir = args.dest_dir.resolve() if args.dest_dir else src.parent.parent / "03_approved_outputs"
    dest = dest_dir / src.name

    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    print(f"Copied: {src}")
    print(f"     -> {dest}")


if __name__ == "__main__":
    main()
