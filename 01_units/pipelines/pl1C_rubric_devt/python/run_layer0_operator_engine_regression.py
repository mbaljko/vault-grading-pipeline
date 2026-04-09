#!/usr/bin/env python3
"""Run fixture-based regression checks for the Layer 0 operator engine."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from layer0_runtime import execute_batch_from_spec_path


def parse_args() -> argparse.Namespace:
	default_manifest = (
		Path(__file__).resolve().parent
		/ "layer0_runtime"
		/ "fixtures"
		/ "operator_engine_regression_manifest.json"
	)
	parser = argparse.ArgumentParser(description="Run Layer 0 operator engine regression fixtures.")
	parser.add_argument(
		"--manifest",
		type=Path,
		default=default_manifest,
		help="Path to the regression fixture manifest JSON.",
	)
	return parser.parse_args()


def _pretty(value: object) -> str:
	return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)


def _load_manifest(path: Path) -> dict[str, object]:
	manifest_path = path.resolve()
	if not manifest_path.exists():
		raise FileNotFoundError(f"Regression manifest not found: {manifest_path}")
	payload = json.loads(manifest_path.read_text(encoding="utf-8"))
	if not isinstance(payload.get("cases"), list):
		raise ValueError("Regression manifest must contain a list under 'cases'.")
	return payload


def _execute_case(case: dict[str, object], fixture_root: Path) -> None:
	case_id = str(case.get("case_id", "")).strip()
	if not case_id:
		raise ValueError("Regression case is missing case_id.")
	spec_file = str(case.get("spec_file", "")).strip()
	if not spec_file:
		raise ValueError(f"Regression case {case_id!r} is missing spec_file.")
	rows = case.get("rows")
	if not isinstance(rows, list):
		raise ValueError(f"Regression case {case_id!r} must provide a rows list.")
	spec_path = (fixture_root / spec_file).resolve()
	expected_error = str(case.get("expected_error", "")).strip()
	if expected_error:
		try:
			execute_batch_from_spec_path(rows, str(spec_path))
		except Exception as exc:  # noqa: BLE001
			message = str(exc)
			if expected_error not in message:
				raise AssertionError(
					f"Case {case_id!r} raised the wrong error.\nExpected substring: {expected_error!r}\nActual: {message!r}"
				) from exc
			return
		raise AssertionError(f"Case {case_id!r} was expected to fail but succeeded.")

	results, diagnostics = execute_batch_from_spec_path(rows, str(spec_path))
	actual_results = [asdict(result) for result in results]
	actual_diagnostics = [asdict(diagnostic) for diagnostic in diagnostics]
	expected_results = case.get("expected_results", [])
	expected_diagnostics = case.get("expected_diagnostics", [])
	if actual_results != expected_results:
		raise AssertionError(
			f"Case {case_id!r} produced unexpected results.\nExpected:\n{_pretty(expected_results)}\nActual:\n{_pretty(actual_results)}"
		)
	if actual_diagnostics != expected_diagnostics:
		raise AssertionError(
			f"Case {case_id!r} produced unexpected diagnostics.\nExpected:\n{_pretty(expected_diagnostics)}\nActual:\n{_pretty(actual_diagnostics)}"
		)


def main() -> int:
	args = parse_args()
	manifest = _load_manifest(args.manifest)
	fixture_root = args.manifest.resolve().parent
	cases = manifest["cases"]
	passed = 0
	for raw_case in cases:
		if not isinstance(raw_case, dict):
			raise ValueError("Each regression case must be an object.")
		_execute_case(raw_case, fixture_root)
		print(f"PASS {raw_case['case_id']}")
		passed += 1
	print(f"All Layer 0 operator engine regression cases passed: {passed}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())