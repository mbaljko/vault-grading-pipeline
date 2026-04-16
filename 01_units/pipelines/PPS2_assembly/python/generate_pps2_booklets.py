#!/usr/bin/env python3
"""Generate individualized PPS2 PDF booklets from a Markdown template and JSON data.

Usage:
    python generate_pps2_booklets.py \
        --template /Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/master_PPS2_activity/PPS2_template.md \
        --input-dir /Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/student_data \
        --output-dir /Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/generated_individualized_PPS2

Expected placeholder format:
    {participant_id}
    {PPP_A1_text}
    {claims.CLM_01_text}

Example student JSON shape:
    {
      "participant_id": "S042",
      "PPP_A1_text": "Example text",
      "claims": {
        "CLM_01_text": "Claim text"
      }
    }
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any


PLACEHOLDER_PATTERN = re.compile(r"\{([A-Za-z0-9_.-]+)\}")
DEFAULT_LATEX_ENGINES = ("xelatex", "lualatex", "pdflatex")


@dataclass(frozen=True)
class RenderResult:
    """Outcome for one student render attempt."""

    student_file: Path
    participant_id: str
    status: str
    message: str


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Render one PPS2 booklet PDF per student JSON file.",
    )
    parser.add_argument(
        "--template",
        type=Path,
        required=True,
        help="Path to the master Markdown template.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing student JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where PDFs will be written.",
    )
    parser.add_argument(
        "--keep-md",
        action="store_true",
        help="Keep the filled intermediate Markdown files next to the PDFs.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Allow unresolved placeholders and continue rendering.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print additional details during processing.",
    )
    return parser.parse_args()


def flatten_json(data: Any, prefix: str = "") -> dict[str, str]:
    """Flatten nested JSON into dot-delimited keys mapped to string values.

    Lists are indexed numerically, for example "items.0.name".
    Scalar values are converted to strings, except null which becomes an empty string.
    """
    flattened: dict[str, str] = {}

    if isinstance(data, dict):
        for key, value in data.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(flatten_json(value, next_prefix))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            next_prefix = f"{prefix}.{index}" if prefix else str(index)
            flattened.update(flatten_json(value, next_prefix))
    else:
        if not prefix:
            raise ValueError("Cannot flatten a non-container JSON value at the root.")
        flattened[prefix] = "" if data is None else str(data)

    return flattened


def build_placeholder_context(data: dict[str, Any]) -> dict[str, str]:
    """Build a placeholder lookup supporting direct keys and flattened nested keys."""
    context = flatten_json(data)
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            continue
        context[str(key)] = "" if value is None else str(value)
    return context


def extract_placeholders(template_text: str) -> set[str]:
    """Extract unique placeholder names from the Markdown template."""
    return set(PLACEHOLDER_PATTERN.findall(template_text))


def fill_template(template_text: str, values: dict[str, str]) -> tuple[str, list[str]]:
    """Replace placeholders in the template with literal text values.

    Returns the rendered text and a sorted list of unresolved placeholders.
    """
    unresolved: set[str] = set()

    def replacer(match: re.Match[str]) -> str:
        placeholder = match.group(1)
        if placeholder in values:
            return values[placeholder]
        unresolved.add(placeholder)
        return match.group(0)

    rendered_text = PLACEHOLDER_PATTERN.sub(replacer, template_text)
    return rendered_text, sorted(unresolved)


def ensure_runtime_dependencies() -> tuple[Path | None, str | None]:
    """Locate pandoc and an available LaTeX engine.

    Pandoc is required. A LaTeX engine is optional if pandoc can write PDF without one,
    but in practice this script prefers an explicit engine when available.
    """
    pandoc_path = shutil.which("pandoc")
    if pandoc_path is None:
        return None, None

    for engine in DEFAULT_LATEX_ENGINES:
        if shutil.which(engine):
            return Path(pandoc_path), engine

    return Path(pandoc_path), None


def render_pdf(
    filled_markdown_path: Path,
    pdf_output_path: Path,
    pandoc_path: Path,
    latex_engine: str | None,
    verbose: bool,
) -> tuple[bool, str]:
    """Convert a filled Markdown file to PDF using pandoc."""
    commands: list[list[str]] = []
    base_command = [str(pandoc_path), str(filled_markdown_path), "-o", str(pdf_output_path)]
    if latex_engine is not None:
        commands.append([*base_command, "--pdf-engine", latex_engine])
    commands.append(base_command)

    attempted: set[tuple[str, ...]] = set()
    last_error = "Unknown pandoc failure"

    for command in commands:
        command_key = tuple(command)
        if command_key in attempted:
            continue
        attempted.add(command_key)
        if verbose:
            print(f"Running: {' '.join(command)}")
        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            if verbose and completed.stdout.strip():
                print(completed.stdout.strip())
            return True, "rendered successfully"
        except subprocess.CalledProcessError as error:
            stderr = (error.stderr or "").strip()
            stdout = (error.stdout or "").strip()
            details = stderr or stdout or str(error)
            last_error = details
            if verbose:
                print(details, file=sys.stderr)

    return False, last_error


def load_student_json(student_file: Path) -> dict[str, Any]:
    """Load and parse one student JSON file as UTF-8."""
    with student_file.open("r", encoding="utf-8") as handle:
        parsed = json.load(handle)
    if not isinstance(parsed, dict):
        raise ValueError("Student JSON root must be an object.")
    return parsed


def render_student(
    student_file: Path,
    template_text: str,
    placeholders: set[str],
    output_dir: Path,
    pandoc_path: Path,
    latex_engine: str | None,
    keep_md: bool,
    allow_missing: bool,
    verbose: bool,
) -> RenderResult:
    """Render one student booklet from JSON into PDF."""
    try:
        student_data = load_student_json(student_file)
    except (json.JSONDecodeError, OSError, ValueError) as error:
        return RenderResult(student_file, student_file.stem, "failed", f"JSON error: {error}")

    participant_id = str(student_data.get("participant_id") or student_file.stem)
    context = build_placeholder_context(student_data)
    rendered_text, unresolved = fill_template(template_text, context)

    missing_placeholders = sorted(set(unresolved) | {item for item in placeholders if item not in context})
    if missing_placeholders and not allow_missing:
        message = f"unresolved placeholders: {', '.join(missing_placeholders)}"
        return RenderResult(student_file, participant_id, "skipped", message)

    pdf_output_path = output_dir / f"{participant_id}_PPS2.pdf"
    md_output_path = output_dir / f"{participant_id}_PPS2.md"

    with TemporaryDirectory(prefix=f"pps2_{participant_id}_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        temp_markdown_path = temp_dir / f"{participant_id}_PPS2.md"
        temp_markdown_path.write_text(rendered_text, encoding="utf-8")

        success, message = render_pdf(
            filled_markdown_path=temp_markdown_path,
            pdf_output_path=pdf_output_path,
            pandoc_path=pandoc_path,
            latex_engine=latex_engine,
            verbose=verbose,
        )
        if not success:
            return RenderResult(student_file, participant_id, "failed", f"PDF conversion error: {message}")

        if keep_md:
            md_output_path.write_text(rendered_text, encoding="utf-8")

    if missing_placeholders:
        return RenderResult(
            student_file,
            participant_id,
            "succeeded",
            f"rendered with unresolved placeholders allowed: {', '.join(missing_placeholders)}",
        )

    return RenderResult(student_file, participant_id, "succeeded", "rendered successfully")


def validate_paths(template_path: Path, input_dir: Path, output_dir: Path) -> None:
    """Validate required paths before processing."""
    if not template_path.is_file():
        raise FileNotFoundError(f"Template file not found: {template_path}")
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)


def print_status(result: RenderResult) -> None:
    """Print one concise status line for a student file."""
    print(f"{result.student_file.name}: {result.status} - {result.message}")


def print_summary(total: int, succeeded: int, skipped: int, failed: int) -> None:
    """Print a concise summary after all files are processed."""
    print("Summary:")
    print(f"  total JSON files found: {total}")
    print(f"  succeeded: {succeeded}")
    print(f"  skipped: {skipped}")
    print(f"  failed: {failed}")


def main() -> int:
    """Run the PPS2 booklet generation workflow."""
    args = parse_args()

    try:
        validate_paths(args.template, args.input_dir, args.output_dir)
    except FileNotFoundError as error:
        print(str(error), file=sys.stderr)
        return 1

    pandoc_path, latex_engine = ensure_runtime_dependencies()
    if pandoc_path is None:
        print("Missing dependency: pandoc was not found on PATH.", file=sys.stderr)
        return 1

    if args.verbose:
        if latex_engine is None:
            print("Pandoc found, but no LaTeX engine detected. Pandoc will be tried without --pdf-engine.")
        else:
            print(f"Using pandoc at {pandoc_path} with LaTeX engine {latex_engine}.")

    try:
        template_text = args.template.read_text(encoding="utf-8")
    except OSError as error:
        print(f"Failed to read template: {error}", file=sys.stderr)
        return 1

    placeholders = extract_placeholders(template_text)
    student_files = sorted(args.input_dir.glob("*.json"))

    succeeded = 0
    skipped = 0
    failed = 0

    for student_file in student_files:
        result = render_student(
            student_file=student_file,
            template_text=template_text,
            placeholders=placeholders,
            output_dir=args.output_dir,
            pandoc_path=pandoc_path,
            latex_engine=latex_engine,
            keep_md=args.keep_md,
            allow_missing=args.allow_missing,
            verbose=args.verbose,
        )
        print_status(result)
        if result.status == "succeeded":
            succeeded += 1
        elif result.status == "skipped":
            skipped += 1
        else:
            failed += 1

    print_summary(len(student_files), succeeded, skipped, failed)
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())