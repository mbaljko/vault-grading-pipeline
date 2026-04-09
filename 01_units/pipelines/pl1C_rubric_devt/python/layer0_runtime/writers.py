from __future__ import annotations

import json
from pathlib import Path

from .models import ExtractionResult, RuntimeDiagnostic


CSV_HEADER = [
	"submission_id",
	"component_id",
	"operator_id",
	"segment_id",
	"segment_text",
	"extraction_status",
	"extraction_notes",
	"confidence",
	"flags",
]


def _quote_csv_text(value: str) -> str:
	escaped = value.replace('"', '""')
	return f'"{escaped}"'


def write_results_csv(path: str, results: list[ExtractionResult]) -> None:
	output_path = Path(path).resolve()
	output_path.parent.mkdir(parents=True, exist_ok=True)
	lines = [",".join(CSV_HEADER)]
	for result in results:
		lines.append(
			",".join(
				[
					result.submission_id,
					result.component_id,
					result.operator_id,
					result.segment_id,
					_quote_csv_text(result.segment_text),
					result.extraction_status,
					_quote_csv_text(result.extraction_notes),
					result.confidence,
					result.flags,
				]
			)
		)
	output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_diagnostics_jsonl(path: str, diagnostics: list[RuntimeDiagnostic]) -> None:
	output_path = Path(path).resolve()
	output_path.parent.mkdir(parents=True, exist_ok=True)
	with output_path.open("w", encoding="utf-8") as handle:
		for diagnostic in diagnostics:
			handle.write(json.dumps(diagnostic.__dict__, ensure_ascii=False) + "\n")