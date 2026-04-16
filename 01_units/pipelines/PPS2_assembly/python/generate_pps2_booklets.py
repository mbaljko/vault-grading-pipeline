#!/usr/bin/env python3
"""Generate individualized PPS2 PDF booklets from a Markdown template and JSON data.

Usage:
    python generate_pps2_booklets.py \
        --template /Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/master_PPS2_activity/PPS2_template.md \
        --latex-template /Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/master_PPS2_activity/PPS2_pdf_template.tex \
        --input-dir /Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/student_data \
        --output-dir /Users/mb/Documents/Vaults/vault-eecs3000w26/Internal/06_grading/PPS2-creation/generated_individualized_PPS2 \
        --keep-tex

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
import csv
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
PAGE_BREAK_PATTERN = re.compile(
    r'<div\b[^>]*class\s*=\s*(["\'])[^"\']*\bpage-break\b[^"\']*\1[^>]*>\s*</div>',
    re.IGNORECASE,
)
DEFAULT_LATEX_ENGINES = ("xelatex", "lualatex", "pdflatex")


@dataclass(frozen=True)
class RenderResult:
    """Outcome for one student render attempt."""

    student_file: Path
    participant_id: str
    pdf_file: Path
    status: str
    message: str


@dataclass(frozen=True)
class StudentRecord:
    """Validated student input ready for rendering."""

    student_file: Path
    participant_id: str
    output_stem: str
    student_data: dict[str, Any]


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
        "--latex-template",
        type=Path,
        help="Optional path to a custom LaTeX template passed to pandoc.",
    )
    parser.add_argument(
        "--keep-md",
        action="store_true",
        help="Keep the filled intermediate Markdown files next to the PDFs.",
    )
    parser.add_argument(
        "--keep-tex",
        action="store_true",
        help="Keep the pandoc-generated LaTeX file next to the PDFs.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Allow unresolved placeholders and continue rendering.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and report what would be rendered without creating PDFs.",
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


def escape_latex_text(value: str) -> str:
    """Escape LaTeX-sensitive characters in dynamic text fragments."""
    replacements = {
        "\\": r"\textbackslash{}",
        "{": r"\{",
        "}": r"\}",
        "#": r"\#",
        "$": r"\$",
        "%": r"\%",
        "&": r"\&",
        "_": r"\_",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in value)


def build_final_page_block(student_data: dict[str, Any]) -> str:
    """Build the appended final page content from student name fields."""
    family_name = escape_latex_text(str(student_data.get("FAMILY_NAME") or "").strip().upper())
    given_name = escape_latex_text(str(student_data.get("GIVEN_NAME") or "").strip())

    if not family_name or not given_name:
        raise ValueError("Final page requires both FAMILY_NAME and GIVEN_NAME.")

    return (
        "\\thispagestyle{empty}\n"
        "\\begin{center}\n"
        "\\vspace*{\\fill}\n"
        "{\\fontsize{18}{22}\\selectfont \\bfseries THIS IS AN INDIVIDUALIZED BOOKLET.\\par}\n"
        "\\vspace{2em}\n"
        "{\\fontsize{20}{24}\\selectfont \\bfseries THIS BOOKLET IS FOR:\\par}\n"
        "\\vspace{2em}\n"
        "{\\fontsize{36}{44}\\selectfont \\bfseries "
        f"{family_name}\\par}}\n"
        "\\vspace{1.5em}\n"
        "{\\fontsize{36}{44}\\selectfont \\bfseries "
        f"{given_name}\\par}}\n"
        "\\vspace*{\\fill}\n"
        "\\end{center}\n"
    )


def apply_rendering_conversions(rendered_text: str, student_data: dict[str, Any]) -> str:
    """Convert supported source-only markup patterns into Pandoc-friendly output.

    This currently translates the HTML page-break marker used in the source markdown
    into a raw LaTeX page break so PDF and emitted .tex output preserve pagination.
    It also appends a final even-numbered page showing the student's name.
    """
    converted_text = PAGE_BREAK_PATTERN.sub(lambda _: "\n\n\\newpage\n\n", rendered_text)
    converted_text = converted_text.rstrip()
    final_page = (
        "\n\n"
        "\\clearpage\n"
        "\\ifodd\\value{page}\n"
        "\\thispagestyle{empty}\n"
        "\\noindent This page deliberately left blank\\par\n"
        "\\clearpage\n"
        "\\fi\n"
        f"{build_final_page_block(student_data)}"
    )
    return f"{converted_text}{final_page}"


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


def split_name_tokens(raw_value: str) -> list[str]:
    """Split a name into filesystem-safe alphanumeric tokens."""
    tokens: list[str] = []
    current: list[str] = []

    for char in raw_value.strip():
        if char.isalnum():
            current.append(char)
            continue
        if current:
            tokens.append("".join(current))
            current = []

    if current:
        tokens.append("".join(current))

    return tokens


def build_output_stem(student_data: dict[str, Any]) -> str:
    """Build the output filename stem from family and given name fields."""
    family_tokens = split_name_tokens(str(student_data.get("FAMILY_NAME") or ""))
    given_tokens = split_name_tokens(str(student_data.get("GIVEN_NAME") or ""))

    if not family_tokens or not given_tokens:
        raise ValueError("Output filename requires both FAMILY_NAME and GIVEN_NAME.")

    family_name = "_".join(token.upper() for token in family_tokens)
    given_name = "_".join(token[:1].upper() + token[1:].lower() for token in given_tokens)
    return f"eecs3000w26_{family_name}_{given_name}"


def format_command_for_log(command: list[str]) -> str:
    """Format a subprocess command for concise logging and error messages."""
    return " ".join(command)


def format_pandoc_error(command: list[str], error: BaseException) -> str:
    """Build a concise, user-facing message for pandoc failures."""
    command_text = format_command_for_log(command)

    if isinstance(error, subprocess.CalledProcessError):
        stderr = (error.stderr or "").strip()
        stdout = (error.stdout or "").strip()
        detail = stderr or stdout or "no stderr/stdout captured"
        return f"pandoc command failed with exit code {error.returncode}: {command_text} | {detail}"

    if isinstance(error, FileNotFoundError):
        return f"pandoc executable not found while running: {command_text}"

    if isinstance(error, OSError):
        return f"OS error while running pandoc command {command_text}: {error}"

    return f"unexpected error while running pandoc command {command_text}: {error}"


def render_pdf(
    filled_markdown_path: Path,
    pdf_output_path: Path,
    pandoc_path: Path,
    latex_engine: str | None,
    latex_template: Path | None,
    verbose: bool,
) -> tuple[bool, str]:
    """Convert a filled Markdown file to PDF using pandoc."""
    commands: list[list[str]] = []
    base_command = [str(pandoc_path), str(filled_markdown_path), "-o", str(pdf_output_path)]
    if latex_template is not None:
        base_command.extend(["--template", str(latex_template)])
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
        except (subprocess.CalledProcessError, FileNotFoundError, OSError) as error:
            last_error = format_pandoc_error(command, error)
            if verbose:
                print(last_error, file=sys.stderr)

    return False, last_error


def render_tex(
    filled_markdown_path: Path,
    tex_output_path: Path,
    pandoc_path: Path,
    latex_template: Path | None,
    verbose: bool,
) -> tuple[bool, str]:
    """Convert a filled Markdown file to LaTeX using pandoc."""
    command = [str(pandoc_path), str(filled_markdown_path), "-t", "latex", "-o", str(tex_output_path)]
    if latex_template is not None:
        command.extend(["--template", str(latex_template)])

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
        return True, "saved LaTeX successfully"
    except (subprocess.CalledProcessError, FileNotFoundError, OSError) as error:
        details = format_pandoc_error(command, error)
        if verbose:
            print(details, file=sys.stderr)
        return False, details


def load_student_record(student_file: Path) -> StudentRecord:
    """Load, parse, and normalize one student JSON file as UTF-8."""
    with student_file.open("r", encoding="utf-8") as handle:
        parsed = json.load(handle)
    if not isinstance(parsed, dict):
        raise ValueError("Student JSON root must be an object.")
    participant_id = str(parsed.get("participant_id") or student_file.stem)
    output_stem = build_output_stem(parsed)
    return StudentRecord(
        student_file=student_file,
        participant_id=participant_id,
        output_stem=output_stem,
        student_data=parsed,
    )


def find_duplicate_participant_ids(student_records: list[StudentRecord]) -> dict[str, list[Path]]:
    """Return duplicate participant IDs mapped to the files that claim them."""
    by_participant: dict[str, list[Path]] = {}
    for record in student_records:
        by_participant.setdefault(record.participant_id, []).append(record.student_file)
    return {
        participant_id: files
        for participant_id, files in by_participant.items()
        if len(files) > 1
    }


def build_duplicate_result(student_record: StudentRecord, duplicate_files: list[Path], output_dir: Path) -> RenderResult:
    """Build a failure result for duplicate participant IDs."""
    other_files = ", ".join(file.name for file in duplicate_files)
    return RenderResult(
        student_file=student_record.student_file,
        participant_id=student_record.participant_id,
        pdf_file=output_dir / f"{student_record.output_stem}.pdf",
        status="failed",
        message=f"duplicate participant_id '{student_record.participant_id}' found in: {other_files}",
    )


def render_student(
    student_record: StudentRecord,
    template_text: str,
    placeholders: set[str],
    output_dir: Path,
    pandoc_path: Path | None,
    latex_engine: str | None,
    latex_template: Path | None,
    keep_md: bool,
    keep_tex: bool,
    allow_missing: bool,
    dry_run: bool,
    verbose: bool,
) -> RenderResult:
    """Render one student booklet from JSON into PDF."""
    participant_id = student_record.participant_id
    student_file = student_record.student_file
    context = build_placeholder_context(student_record.student_data)
    rendered_text, unresolved = fill_template(template_text, context)
    rendered_text = apply_rendering_conversions(rendered_text, student_record.student_data)

    missing_placeholders = sorted(set(unresolved) | {item for item in placeholders if item not in context})
    if missing_placeholders and not allow_missing:
        message = f"unresolved placeholders: {', '.join(missing_placeholders)}"
        return RenderResult(student_file, participant_id, output_dir / f"{student_record.output_stem}.pdf", "skipped", message)

    pdf_output_path = output_dir / f"{student_record.output_stem}.pdf"
    md_output_path = output_dir / f"{student_record.output_stem}.md"
    tex_output_path = output_dir / f"{student_record.output_stem}.tex"

    if dry_run:
        if missing_placeholders:
            return RenderResult(
                student_file,
                participant_id,
                pdf_output_path,
                "dry-run",
                f"would render with unresolved placeholders allowed: {', '.join(missing_placeholders)}",
            )
        return RenderResult(student_file, participant_id, pdf_output_path, "dry-run", "would render successfully")

    if pandoc_path is None:
        return RenderResult(student_file, participant_id, pdf_output_path, "failed", "pandoc path was not configured")

    with TemporaryDirectory(prefix=f"pps2_{participant_id}_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        temp_markdown_path = temp_dir / f"{student_record.output_stem}.md"
        temp_markdown_path.write_text(rendered_text, encoding="utf-8")

        success, message = render_pdf(
            filled_markdown_path=temp_markdown_path,
            pdf_output_path=pdf_output_path,
            pandoc_path=pandoc_path,
            latex_engine=latex_engine,
            latex_template=latex_template,
            verbose=verbose,
        )
        if not success:
            return RenderResult(student_file, participant_id, pdf_output_path, "failed", f"PDF conversion error: {message}")

        if keep_md:
            md_output_path.write_text(rendered_text, encoding="utf-8")

        if keep_tex:
            tex_success, tex_message = render_tex(
                filled_markdown_path=temp_markdown_path,
                tex_output_path=tex_output_path,
                pandoc_path=pandoc_path,
                latex_template=latex_template,
                verbose=verbose,
            )
            if not tex_success:
                return RenderResult(student_file, participant_id, pdf_output_path, "failed", f"LaTeX conversion error: {tex_message}")

    if missing_placeholders:
        return RenderResult(
            student_file,
            participant_id,
            pdf_output_path,
            "succeeded",
            f"rendered with unresolved placeholders allowed: {', '.join(missing_placeholders)}",
        )

    return RenderResult(student_file, participant_id, pdf_output_path, "succeeded", "rendered successfully")


def validate_paths(
    template_path: Path,
    input_dir: Path,
    output_dir: Path,
    latex_template_path: Path | None,
) -> None:
    """Validate required paths before processing."""
    if not template_path.is_file():
        raise FileNotFoundError(f"Template file not found: {template_path}")
    if not input_dir.is_dir():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")
    if latex_template_path is not None and not latex_template_path.is_file():
        raise FileNotFoundError(f"LaTeX template file not found: {latex_template_path}")
    output_dir.mkdir(parents=True, exist_ok=True)


def print_status(result: RenderResult) -> None:
    """Print one concise status line for a student file."""
    print(f"{result.student_file.name}: {result.status} - {result.message}")


def print_summary(total: int, succeeded: int, skipped: int, failed: int) -> None:
    """Print a concise summary after all files are processed."""
    print("Summary:")
    print(f"  total JSON files found: {total}")
    print(f"  succeeded: {succeeded}")
    print(f"  dry-run: {0}")
    print(f"  skipped: {skipped}")
    print(f"  failed: {failed}")


def write_manifest(output_dir: Path, results: list[RenderResult]) -> Path:
    """Write a CSV manifest describing the render results."""
    manifest_path = output_dir / "render_manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["participant_id", "json_file", "pdf_file", "status", "notes"],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "participant_id": result.participant_id,
                    "json_file": result.student_file.name,
                    "pdf_file": result.pdf_file.name,
                    "status": result.status,
                    "notes": result.message,
                }
            )
    return manifest_path


def main() -> int:
    """Run the PPS2 booklet generation workflow."""
    args = parse_args()

    try:
        validate_paths(args.template, args.input_dir, args.output_dir, args.latex_template)
    except FileNotFoundError as error:
        print(str(error), file=sys.stderr)
        return 1

    pandoc_path: Path | None = None
    latex_engine: str | None = None
    if not args.dry_run:
        pandoc_path, latex_engine = ensure_runtime_dependencies()
        if pandoc_path is None:
            print("Missing dependency: pandoc was not found on PATH.", file=sys.stderr)
            return 1

    if args.verbose:
        if args.dry_run:
            print("Dry-run mode enabled: no PDF or LaTeX files will be rendered.")
        elif latex_engine is None:
            print("Pandoc found, but no LaTeX engine detected. Pandoc will be tried without --pdf-engine.")
        else:
            print(f"Using pandoc at {pandoc_path} with LaTeX engine {latex_engine}.")
        if args.latex_template is not None:
            print(f"Using custom LaTeX template at {args.latex_template}.")

    try:
        template_text = args.template.read_text(encoding="utf-8")
    except OSError as error:
        print(f"Failed to read template: {error}", file=sys.stderr)
        return 1

    placeholders = extract_placeholders(template_text)
    student_files = sorted(args.input_dir.glob("*.json"))

    succeeded = 0
    dry_run_count = 0
    skipped = 0
    failed = 0
    results: list[RenderResult] = []
    student_records: list[StudentRecord] = []

    for student_file in student_files:
        try:
            student_records.append(load_student_record(student_file))
        except (json.JSONDecodeError, OSError, ValueError) as error:
            result = RenderResult(
                student_file=student_file,
                participant_id=student_file.stem,
                pdf_file=args.output_dir / f"{student_file.stem}.pdf",
                status="failed",
                message=f"JSON error: {error}",
            )
            results.append(result)
            print_status(result)
            failed += 1

    duplicate_participant_ids = find_duplicate_participant_ids(student_records)

    for student_record in student_records:
        if student_record.participant_id in duplicate_participant_ids:
            result = build_duplicate_result(
                student_record,
                duplicate_participant_ids[student_record.participant_id],
                args.output_dir,
            )
        else:
            result = render_student(
                student_record=student_record,
                template_text=template_text,
                placeholders=placeholders,
                output_dir=args.output_dir,
                pandoc_path=pandoc_path,
                latex_engine=latex_engine,
                latex_template=args.latex_template,
                keep_md=args.keep_md,
                keep_tex=args.keep_tex,
                allow_missing=args.allow_missing,
                dry_run=args.dry_run,
                verbose=args.verbose,
            )

        results.append(result)
        print_status(result)
        if result.status == "succeeded":
            succeeded += 1
        elif result.status == "dry-run":
            dry_run_count += 1
        elif result.status == "skipped":
            skipped += 1
        else:
            failed += 1

    try:
        manifest_path = write_manifest(args.output_dir, results)
    except OSError as error:
        print(f"Failed to write manifest CSV: {error}", file=sys.stderr)
        return 1

    if args.verbose:
        print(f"Wrote manifest: {manifest_path}")

    print("Summary:")
    print(f"  total JSON files found: {len(student_files)}")
    print(f"  succeeded: {succeeded}")
    print(f"  dry-run: {dry_run_count}")
    print(f"  skipped: {skipped}")
    print(f"  failed: {failed}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())