#!/usr/bin/env python3
"""Render one markdown file to PDF through the PPS2 pandoc/LaTeX pipeline."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from generate_pps2_booklets import (
    PAGE_BREAK_PATTERN,
    UNICODE_LATEX_REPLACEMENTS,
    ensure_runtime_dependencies,
    inject_marks_into_template,
    load_injected_marks_map,
    number_question_placeholders,
    render_pdf,
    render_tex,
    replace_answer_box_markers,
    replace_combining_enclosing_circle,
    replace_full_width_rules,
)


HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a standalone markdown file to PDF using the PPS2 LaTeX pipeline.")
    parser.add_argument("--markdown-path", type=Path, required=True, help="Path to the source markdown file.")
    parser.add_argument("--output-pdf-path", type=Path, required=True, help="Path to the output PDF file.")
    parser.add_argument("--latex-template", type=Path, help="Optional custom LaTeX template passed to pandoc.")
    parser.add_argument("--header-name", default="PPS2 Instructions", help="Value passed as student_header_name to the LaTeX template.")
    parser.add_argument("--keep-tex", action="store_true", help="Also emit the intermediate LaTeX file next to the PDF.")
    parser.add_argument("--verbose", action="store_true", help="Print pandoc command details.")
    return parser.parse_args()


def preprocess_standalone_markdown(source_markdown: str) -> str:
    """Apply only the markdown-to-LaTeX safety conversions needed for standalone renders."""

    rendered = number_question_placeholders(source_markdown)
    rendered = inject_short_heading_marks(rendered)
    rendered = replace_full_width_rules(rendered)
    rendered = replace_combining_enclosing_circle(rendered)
    for source, replacement in UNICODE_LATEX_REPLACEMENTS.items():
        rendered = rendered.replace(source, replacement)
    rendered = replace_answer_box_markers(rendered)
    rendered = PAGE_BREAK_PATTERN.sub(lambda _: "\n\n\\newpage\n\n", rendered)
    return rendered


def build_short_heading_text(heading_text: str) -> str:
    """Build a short running-header label from the final three heading words."""

    cleaned = heading_text.replace("(", " ").replace(")", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return ""
    words = [word.strip(".,:;!?[]{}") for word in cleaned.split()]
    words = [word for word in words if word]
    return " ".join(words[-3:])


def inject_short_heading_marks(markdown_text: str) -> str:
    """Insert raw LaTeX marks after markdown headings for short center headers."""

    rendered_lines: list[str] = []
    for line in markdown_text.splitlines():
        rendered_lines.append(line)
        match = HEADING_PATTERN.match(line)
        if not match:
            continue
        short_heading = build_short_heading_text(match.group(2))
        if short_heading:
            rendered_lines.append(rf"\markright{{{short_heading}}}")
    return "\n".join(rendered_lines)


def main() -> int:
    args = parse_args()

    if not args.markdown_path.is_file():
        print(f"Markdown file not found: {args.markdown_path}", file=sys.stderr)
        return 1
    if args.latex_template is not None and not args.latex_template.is_file():
        print(f"LaTeX template file not found: {args.latex_template}", file=sys.stderr)
        return 1

    pandoc_path, latex_engine = ensure_runtime_dependencies()
    if pandoc_path is None:
        print("Missing dependency: pandoc was not found on PATH.", file=sys.stderr)
        return 1

    try:
        source_markdown = args.markdown_path.read_text(encoding="utf-8")
    except OSError as error:
        print(f"Failed to read markdown source: {error}", file=sys.stderr)
        return 1

    if "(z marks)" in source_markdown:
        marks_path = args.markdown_path.parent / "injection_marks.md"
        try:
            marks_by_heading = load_injected_marks_map(marks_path)
        except (OSError, ValueError) as error:
            print(f"Failed to load injection marks: {error}", file=sys.stderr)
            return 1
        source_markdown = inject_marks_into_template(source_markdown, marks_by_heading)

    rendered_markdown = preprocess_standalone_markdown(source_markdown)
    args.output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    temp_markdown_path = args.output_pdf_path.with_suffix(".rendered.md")
    temp_markdown_path.write_text(rendered_markdown, encoding="utf-8")

    try:
        success, message = render_pdf(
            filled_markdown_path=temp_markdown_path,
            pdf_output_path=args.output_pdf_path,
            pandoc_path=pandoc_path,
            latex_engine=latex_engine,
            latex_template=args.latex_template,
            template_variables={"student_header_name": args.header_name, "hide_center_header": "true"},
            verbose=args.verbose,
        )
        if not success:
            print(message, file=sys.stderr)
            return 1

        if args.keep_tex:
            tex_output_path = args.output_pdf_path.with_suffix(".tex")
            tex_success, tex_message = render_tex(
                filled_markdown_path=temp_markdown_path,
                tex_output_path=tex_output_path,
                pandoc_path=pandoc_path,
                latex_template=args.latex_template,
                template_variables={"student_header_name": args.header_name, "hide_center_header": "true"},
                verbose=args.verbose,
            )
            if not tex_success:
                print(tex_message, file=sys.stderr)
                return 1
    finally:
        temp_markdown_path.unlink(missing_ok=True)

    print(f"Produced PDF: {args.output_pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())