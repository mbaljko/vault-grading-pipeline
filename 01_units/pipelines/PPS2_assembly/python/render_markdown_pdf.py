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
    number_question_placeholders,
    render_pdf,
    render_tex,
    replace_answer_box_markers,
    replace_combining_enclosing_circle,
    replace_full_width_rules,
)


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

    rendered = source_markdown
    rendered = number_question_placeholders(rendered)
    rendered = replace_full_width_rules(rendered)
    rendered = replace_combining_enclosing_circle(rendered)
    for source, replacement in UNICODE_LATEX_REPLACEMENTS.items():
        rendered = rendered.replace(source, replacement)
    rendered = replace_answer_box_markers(rendered)
    rendered = PAGE_BREAK_PATTERN.sub(lambda _: "\n\n\\newpage\n\n", rendered)
    return rendered


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
            template_variables={"student_header_name": args.header_name},
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
                template_variables={"student_header_name": args.header_name},
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