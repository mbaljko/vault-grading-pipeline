#!/usr/bin/env python3
"""Compile expanded Layer 0 registry instances into typed OperatorSpec artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generate_schema_from_segmentation_registry import OperatorSpec, build_operator_specs_payload, write_json_output


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Compile expanded registry instances into operator spec JSON and optional Python artifacts."
	)
	parser.add_argument(
		"--expanded-registry",
		type=Path,
		required=True,
		help="Path to the expanded registry instances JSON artifact.",
	)
	parser.add_argument(
		"--operator-specs-output",
		type=Path,
		required=True,
		help="Path to write the compiled operator specs JSON artifact.",
	)
	parser.add_argument(
		"--operator-specs-py-output",
		type=Path,
		help="Optional path to write a Python module containing OperatorSpec instances.",
	)
	return parser.parse_args()


def load_expanded_registry(path: Path) -> dict[str, object]:
	expanded_path = path.resolve()
	data = json.loads(expanded_path.read_text(encoding="utf-8"))
	for required_key in ["assessment_id", "source_registry_version", "expanded_instances"]:
		if required_key not in data:
			raise ValueError(f"Expanded registry is missing required key {required_key!r}.")
	return data


def write_operator_specs_py(output_path: Path, payload: dict[str, object]) -> None:
	operator_specs = payload.get("operator_specs", [])
	if not isinstance(operator_specs, list):
		raise ValueError("operator_specs payload must contain a list under 'operator_specs'.")

	lines: list[str] = [
		"from generate_schema_from_segmentation_registry import OperatorSpec",
		"",
		f"ASSESSMENT_ID = {payload.get('assessment_id', '')!r}",
		f"SOURCE_REGISTRY_VERSION = {payload.get('source_registry_version', '')!r}",
		f"SPEC_VERSION = {payload.get('spec_version', '')!r}",
		"",
		"OPERATOR_SPECS = [",
	]
	for spec_row in operator_specs:
		spec = OperatorSpec(**spec_row)
		lines.append(f"    OperatorSpec(**{spec_row!r}),")
	lines.extend(
		[
			"]",
			"",
			"def get_operator_specs() -> list[OperatorSpec]:",
			"    return OPERATOR_SPECS",
		]
	)
	output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
	args = parse_args()
	expanded_registry_path = args.expanded_registry.resolve()
	if not expanded_registry_path.exists():
		raise FileNotFoundError(f"Expanded registry not found: {expanded_registry_path}")

	expanded_payload = load_expanded_registry(expanded_registry_path)
	operator_specs_payload = build_operator_specs_payload(expanded_payload)
	json_output_path = args.operator_specs_output.resolve()
	json_output_path.parent.mkdir(parents=True, exist_ok=True)
	write_json_output(json_output_path, operator_specs_payload)

	py_output_path: Path | None = None
	if args.operator_specs_py_output is not None:
		py_output_path = args.operator_specs_py_output.resolve()
		py_output_path.parent.mkdir(parents=True, exist_ok=True)
		write_operator_specs_py(py_output_path, operator_specs_payload)

	print(f"Expanded registry: {expanded_registry_path}")
	print(f"Operator specs JSON output: {json_output_path}")
	if py_output_path is not None:
		print(f"Operator specs Python output: {py_output_path}")
	audit = operator_specs_payload.get("audit", {})
	warnings = audit.get("warnings", []) if isinstance(audit, dict) else []
	if warnings:
		print(f"Operator spec audit warnings: {len(warnings)}")
		for warning in warnings:
			print(f"WARNING: {warning}")
	print(f"Operator specs written: {len(operator_specs_payload['operator_specs'])}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())