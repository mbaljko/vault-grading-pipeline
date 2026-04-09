#!/usr/bin/env python3
"""Stub generator for segmentation-registry schema outputs.

This sibling script intentionally mirrors the command-line contract of
generate_rubric_and_manifest_from_indicator_registry.py, but the schema
generation behavior has not been implemented yet.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Generate schema outputs from a Layer 0, 1, 2, 3, or 4 registry."
	)
	parser.add_argument(
		"--registry",
		"--indicator-registry",
		dest="registry_path",
		type=Path,
		required=True,
		help="Path to the markdown registry file.",
	)
	parser.add_argument(
		"--registry-layer",
		choices=["auto", "layer0", "layer1", "layer2", "layer3", "layer4"],
		default="auto",
		help="Registry layer to load. Defaults to auto-detection.",
	)
	parser.add_argument(
		"--output-dir",
		type=Path,
		help="Directory for generated outputs. Defaults to the registry file directory.",
	)
	parser.add_argument(
		"--rubric-output",
		type=Path,
		help="Explicit rubric output file path. Overrides --output-dir naming.",
	)
	parser.add_argument(
		"--manifest-output",
		type=Path,
		help="Explicit manifest output file path. Overrides --output-dir naming.",
	)
	parser.add_argument(
		"--include-inactive",
		action="store_true",
		help="Include rows whose status is not 'active'.",
	)
	return parser.parse_args()


def main() -> int:
	args = parse_args()
	print(
		"Schema generator stub\n"
		f"registry={args.registry_path}\n"
		f"registry_layer={args.registry_layer}\n"
		f"output_dir={args.output_dir}\n"
		f"rubric_output={args.rubric_output}\n"
		f"manifest_output={args.manifest_output}\n"
		f"include_inactive={args.include_inactive}",
		file=sys.stderr,
	)
	print(
		"Error: generate_schema_from_segmentation_registry.py is a stub and has not been implemented yet.",
		file=sys.stderr,
	)
	return 1


if __name__ == "__main__":
	raise SystemExit(main())