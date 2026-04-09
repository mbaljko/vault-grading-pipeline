from __future__ import annotations

import importlib.util
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

from .models import OperatorSpec


KNOWN_FAMILIES = {
	"left_np_before_anchor",
	"right_np_after_anchor_before_marker",
	"span_after_marker_before_marker",
	"local_effect_phrase_after_marker",
	"status_only_anchor_detector",
}


def _spec_dict_from_object(raw_spec: Any) -> dict[str, Any]:
	if isinstance(raw_spec, dict):
		return dict(raw_spec)
	if is_dataclass(raw_spec):
		return asdict(raw_spec)
	return {
		field_name: getattr(raw_spec, field_name)
		for field_name in OperatorSpec.__dataclass_fields__
		if hasattr(raw_spec, field_name)
	}


def _coerce_operator_spec(raw_spec: Any) -> OperatorSpec:
	spec_dict = _spec_dict_from_object(raw_spec)
	return OperatorSpec(**spec_dict)


def _load_specs_from_json(path: Path) -> list[OperatorSpec]:
	payload = json.loads(path.read_text(encoding="utf-8"))
	rows = payload.get("operator_specs", [])
	if not isinstance(rows, list):
		raise ValueError("Operator specs JSON must contain a list under 'operator_specs'.")
	return [_coerce_operator_spec(row) for row in rows]


def _load_module_from_path(path: Path) -> ModuleType:
	module_name = f"layer0_operator_specs_{path.stem}"
	spec = importlib.util.spec_from_file_location(module_name, path)
	if spec is None or spec.loader is None:
		raise ValueError(f"Could not load operator-spec module from {path}")
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def _load_specs_from_py(path: Path) -> list[OperatorSpec]:
	module = _load_module_from_path(path)
	raw_specs = getattr(module, "OPERATOR_SPECS", None)
	if raw_specs is None and hasattr(module, "get_operator_specs"):
		raw_specs = module.get_operator_specs()
	if raw_specs is None:
		raise ValueError(f"Python operator-spec module does not expose OPERATOR_SPECS: {path}")
	return [_coerce_operator_spec(raw_spec) for raw_spec in raw_specs]


def validate_spec(spec: OperatorSpec) -> None:
	for field_name in [
		"assessment_id",
		"component_id",
		"template_id",
		"operator_id",
		"operator_identifier",
		"segment_id",
		"family",
		"instance_status",
	]:
		if not str(getattr(spec, field_name)).strip():
			raise ValueError(f"OperatorSpec is missing required field {field_name!r}: {spec}")
	if spec.output_mode not in {"span", "status_only"}:
		raise ValueError(f"Unsupported output_mode for {spec.operator_id}: {spec.output_mode!r}")
	if spec.family not in KNOWN_FAMILIES:
		raise ValueError(f"Unknown operator family for {spec.operator_id}: {spec.family!r}")
	if spec.instance_status.lower() != "active":
		raise ValueError(f"Inactive OperatorSpec cannot be loaded for execution: {spec.operator_id!r}")
	if spec.family != "status_only_anchor_detector" and not spec.anchor_patterns:
		raise ValueError(f"OperatorSpec requires anchor_patterns: {spec.operator_id!r}")
	if spec.family in {
		"right_np_after_anchor_before_marker",
		"span_after_marker_before_marker",
		"local_effect_phrase_after_marker",
	} and not spec.stop_markers:
		raise ValueError(f"OperatorSpec requires stop_markers: {spec.operator_id!r}")


def validate_specs(specs: list[OperatorSpec]) -> None:
	if not specs:
		raise ValueError("No operator specs were loaded.")
	seen_identifiers: set[str] = set()
	component_operator_pairs: set[tuple[str, str]] = set()
	for spec in specs:
		validate_spec(spec)
		if spec.operator_identifier in seen_identifiers:
			raise ValueError(f"Duplicate operator_identifier in spec set: {spec.operator_identifier!r}")
		seen_identifiers.add(spec.operator_identifier)
		component_operator_pair = (spec.component_id, spec.operator_id)
		if component_operator_pair in component_operator_pairs:
			raise ValueError(f"Duplicate operator_id within component: {component_operator_pair!r}")
		component_operator_pairs.add(component_operator_pair)


def load_operator_specs(path: str) -> list[OperatorSpec]:
	spec_path = Path(path).resolve()
	if not spec_path.exists():
		raise FileNotFoundError(f"Operator specs not found: {spec_path}")
	if spec_path.suffix.lower() == ".json":
		specs = _load_specs_from_json(spec_path)
	elif spec_path.suffix.lower() == ".py":
		specs = _load_specs_from_py(spec_path)
	else:
		raise ValueError(f"Unsupported operator-spec path suffix: {spec_path.suffix!r}")
	validate_specs(specs)
	return specs


def index_specs_by_component(specs: list[OperatorSpec]) -> dict[str, list[OperatorSpec]]:
	validate_specs(specs)
	indexed: dict[str, list[OperatorSpec]] = {}
	for spec in specs:
		indexed.setdefault(spec.component_id, []).append(spec)
	for component_id, component_specs in indexed.items():
		component_specs.sort(key=lambda spec: spec.operator_id)
		if len({spec.operator_id for spec in component_specs}) != len(component_specs):
			raise ValueError(f"Duplicate operator_id within component spec list: {component_id!r}")
	return indexed