#!/usr/bin/env python3
"""Expand a normalized Layer 0 registry into concrete operator-instance rows.

Supported registry field values are documented in:
- `layer0_registry_supported_values.md`
"""

from __future__ import annotations

import argparse
from pathlib import Path

from generate_schema_from_segmentation_registry import expand_registry_instances, load_normalized_registry, write_json_output


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Expand normalized registry templates into concrete component-specific operator instances."
	)
	parser.add_argument(
		"--normalized-registry",
		type=Path,
		required=True,
		help="Path to the normalized registry JSON artifact.",
	)
	parser.add_argument(
		"--expanded-output",
		type=Path,
		required=True,
		help="Path to write the expanded registry instances JSON artifact.",
	)
	return parser.parse_args()


def main() -> int:
	args = parse_args()
	normalized_registry_path = args.normalized_registry.resolve()
	if not normalized_registry_path.exists():
		raise FileNotFoundError(f"Normalized registry not found: {normalized_registry_path}")

	registry = load_normalized_registry(normalized_registry_path)
	expanded_payload = expand_registry_instances(registry)
	output_path = args.expanded_output.resolve()
	output_path.parent.mkdir(parents=True, exist_ok=True)
	write_json_output(output_path, expanded_payload)

	print(f"Normalized registry: {normalized_registry_path}")
	print(f"Expanded registry output: {output_path}")
	print(f"Expanded instances written: {len(expanded_payload['expanded_instances'])}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())