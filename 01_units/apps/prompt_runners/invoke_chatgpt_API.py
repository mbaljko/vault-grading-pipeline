#!/usr/bin/env python3
"""Send prompt instructions and prompt input to the OpenAI Responses API and persist results.

What this script does:
- Resolves prompt instructions and prompt input from CLI args or built-in defaults.
- Calls the OpenAI Responses API.
- Persists extracted output text in requested file formats.

Inputs:
- Prompt instructions (choose one):
    - `--prompt "..."`: inline prompt text.
    - `--prompt-instructions-file path/to/prompt.txt`: prompt loaded from a file path.
- Prompt instructions file parsing (`--prompt-instructions-file`):
        - Default: use the full file content after removing a leading YAML front
            matter block (if present), then apply `.strip()`.
    - With `--use-first-fenced-block`: extract only the first fenced Markdown
            block (``` or ````) from the YAML-stripped content. If no fenced block is
            found, falls back to YAML-stripped full-file text.
    - Empty content after parsing raises a validation error.
- Prompt instructions precedence:
    - At most one of `--prompt` or `--prompt-instructions-file` may be provided.
    - If none is provided, built-in `DEFAULT_USER_PROMPT` is used.
- Prompt input (choose one):
    - `--prompt-input-json '{"key": "value"}'`
    - `--prompt-input-file path/to/input.txt`
- If no prompt input is provided, a built-in sample input is used.
- API call structure:
    - Both are combined into a single user message sent to the API as JSON text with fields:
        `{"prompt_instructions": "...", "prompt_input": "..."}`
    - The system role carries only `SYSTEM_PROMPT`.
    - A system message is included only when `SYSTEM_PROMPT.strip()` is non-empty.
      This keeps strict contract runs free of implicit extra instructions.
      Revert option: always include a system message by removing the conditional branch
      in `build_request_body`.

Outputs:
- The full API response object is always captured in memory.
- `extracted_output_text` is derived from that full API response object.
- A runner metadata sidecar JSON is always written alongside outputs.
- `--output-format <json|csv|md>` (repeatable) selects which artifacts are written:
    - `json`: writes JSON containing `extracted_output_text`.
    - `csv`: writes CSV derived from `extracted_output_text`.
        - If text looks like CSV, rows are parsed and written.
        - Otherwise, a single-column CSV (`output_text`) is written.
    - `md`: writes Markdown with YAML front matter metadata (instructions source, input source, timestamp)
        followed by `extracted_output_text`.
- `--save-full-api-response` controls whether a separate raw API response JSON file is written.
- Output filename patterns:
    - Extracted JSON: `<stem>_output.json`
    - Runner metadata JSON: `<stem>_run_metadata.json`
    - Full API response JSON (only when `--save-full-api-response` is set): `<stem>_api_response.json`
    - CSV: `<stem>_output.csv`
    - Markdown: `<stem>_output.md`
- `--output-file-stem <stem>` optionally overrides `<stem>` for all outputs.
- Output path behavior:
    - If `--output-dir` is provided, all outputs are written there.
    - Otherwise, when a prompt instructions file is provided, outputs are written next to it.
    - Otherwise, outputs are written next to this script file.
- Paths are resolved to absolute paths before writing.

Additional invocation parameters:
- `--temperature <float>`
- `--max-output-tokens <int>`
- `--model <name>`
- `--output-file-stem <stem>`
- `--save-full-api-response`
- `--dry-run`
- `--verbose [true|false]`
- `--use-first-fenced-block`

Environment configuration:
- Optional env vars:
    - `OPENAI_ORG_ID`
    - `OPENAI_PROJECT_ID`
    - `OPENAI_MODEL`
    - `OPENAI_API_BASE_URL`
    - `OPENAI_SYSTEM_PROMPT`
- API key source (exclusive): `secrets/openai_api_key.txt` at repository root.

Example:
        python invoke_chatgpt_API.py \
            --prompt "Summarize this calibration input" \
            --prompt-input-file input.txt
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _extract_first_fenced_block(markdown_text: str) -> str | None:
    """Return content of first fenced block (``` or ````), else None."""
    pattern = re.compile(r"(?ms)^\s*(`{3,4})[^\n`]*\n(.*?)\n\s*\1\s*$")
    match = pattern.search(markdown_text)
    if not match:
        return None
    return match.group(2).strip()


def _strip_leading_yaml_front_matter(text: str) -> str:
    """Remove leading YAML front matter block from Markdown text, if present."""
    pattern = re.compile(r"\A(?:\ufeff)?---[ \t]*\r?\n.*?\r?\n---[ \t]*(?:\r?\n|$)", re.DOTALL)
    match = pattern.match(text)
    if not match:
        return text
    return text[match.end():]


def _find_repo_root(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def load_api_key_from_secrets() -> str:
    """Load API key exclusively from repo-root secrets file."""
    # This script intentionally does NOT read OPENAI_API_KEY from env.
    # Credential source is standardized to the repo secrets directory.
    # Expected location: <repo-root>/secrets/openai_api_key.txt

    script_dir = Path(__file__).resolve().parent
    repo_root = _find_repo_root(script_dir)
    if repo_root is None:
        return ""

    key_file = repo_root / "secrets" / "openai_api_key.txt"
    if not key_file.exists():
        return ""

    return key_file.read_text(encoding="utf-8").strip()


# ==============================
# Account / API configuration
# ==============================
API_KEY = load_api_key_from_secrets()
ORGANIZATION_ID = os.getenv("OPENAI_ORG_ID", "")
PROJECT_ID = os.getenv("OPENAI_PROJECT_ID", "")
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.1")
API_BASE_URL = os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1")
# Intentionally empty by default for strict contract prompting. Override via env when needed.
# Revert option: set default to "You are a helpful assistant." and/or always include system role.
SYSTEM_PROMPT = os.getenv("OPENAI_SYSTEM_PROMPT", "")
REQUEST_TIMEOUT_SECONDS = 600
DEFAULT_USER_PROMPT = (
    "Analyze the provided text segments. Return concise themes, key claims, "
    "and any notable inconsistencies."
)
DEFAULT_PROMPT_INPUT = (
    "Example input segment A.\n"
    "Example input segment B."
)


def _parse_cli_bool(value: str | bool) -> bool:
    """Parse common true/false tokens for CLI flags."""
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(
        "Expected boolean value for --verbose (true/false, yes/no, 1/0)."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send prompt instructions + prompt input to ChatGPT API."
    )
    parser.add_argument("--prompt", help="User prompt text.")
    parser.add_argument(
        "--prompt-instructions-file",
        type=Path,
        help=(
            "Path to a text/Markdown file containing prompt text. "
            "By default the full file is used."
        ),
    )
    parser.add_argument(
        "--use-first-fenced-block",
        action="store_true",
        help=(
            "When set with --prompt-instructions-file, use only the first fenced "
            "Markdown block as the prompt text."
        ),
    )
    parser.add_argument(
        "--prompt-input-file",
        type=Path,
        help="Path to a text/Markdown file containing prompt input (passed as plain text).",
    )
    parser.add_argument(
        "--prompt-input-json",
        help="Inline JSON prompt input string (pretty-printed and passed as text).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Sampling temperature.",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=1.0,
        help="Nucleus sampling probability (top_p).",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=None,
        help="Optional output token cap. If omitted, request does not force a cap.",
    )
    parser.add_argument(
        "--model",
        default=MODEL,
        help="Model name override (default: configured MODEL constant).",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=REQUEST_TIMEOUT_SECONDS,
        help=(
            "HTTP request timeout in seconds for the Responses API call "
            f"(default: {REQUEST_TIMEOUT_SECONDS})."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Optional output directory for generated files. If omitted, outputs are "
            "written next to the prompt instructions file (when provided) or next to "
            "this script."
        ),
    )
    parser.add_argument(
        "--output-format",
        action="append",
        choices=["json", "csv", "md"],
        default=None,
        help=(
            "Select output artifact(s) to write. Repeat to write multiple formats "
            "(for example: --output-format json --output-format csv). "
            "Defaults to json and csv when omitted."
        ),
    )
    parser.add_argument(
        "--save-full-api-response",
        action="store_true",
        help=(
            "When set, write a separate JSON file containing the full raw API response object."
        ),
    )
    parser.add_argument(
        "--output-file-stem",
        type=str,
        default=None,
        help=(
            "Optional filename stem override for all output artifacts. "
            "When omitted, stem is derived from prompt instructions file or falls back "
            "to 'invoke_chatgpt_API'."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Print resolved prompt instructions/prompt input/request body and exit "
            "without calling API."
        ),
    )
    parser.add_argument(
        "--verbose",
        nargs="?",
        const=True,
        default=False,
        type=_parse_cli_bool,
        help=(
            "Print resolved request body JSON and prompt_instructions/prompt_input "
            "diagnostics before invoking the API. Accepts optional true/false; "
            "if value is omitted, defaults to true."
        ),
    )
    return parser.parse_args()


def load_prompt_input(args: argparse.Namespace) -> str:
    """Return prompt input as plain text.

    - ``--prompt-input-file``: full file content is read and returned as-is (plain text).
    - ``--prompt-input-json``: JSON is parsed then pretty-printed back to text.
    - Neither provided: returns ``DEFAULT_PROMPT_INPUT``.
    """
    if args.prompt_input_file and args.prompt_input_json:
        raise ValueError("Provide at most one of --prompt-input-file or --prompt-input-json.")

    if not args.prompt_input_file and not args.prompt_input_json:
        return DEFAULT_PROMPT_INPUT

    if args.prompt_input_file:
        try:
            raw = args.prompt_input_file.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ValueError(f"Prompt input file not found: {args.prompt_input_file}") from exc

        # Keep prompt input fully intact; do not apply fenced-block extraction.
        prompt_input_text = raw.strip()
        if not prompt_input_text:
            raise ValueError(f"Prompt input file is empty: {args.prompt_input_file}")
        return prompt_input_text

    try:
        parsed = json.loads(args.prompt_input_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"--prompt-input-json is not valid JSON: {exc}") from exc
    return json.dumps(parsed, indent=2, ensure_ascii=False)


def load_prompt_instructions(args: argparse.Namespace) -> str:
    provided_count = sum(bool(x) for x in [args.prompt, args.prompt_instructions_file])
    if provided_count > 1:
        raise ValueError("Provide at most one of --prompt or --prompt-instructions-file.")

    prompt_instructions_source = args.prompt_instructions_file

    if prompt_instructions_source:
        try:
            raw = prompt_instructions_source.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ValueError(
                f"Prompt instructions file not found: {prompt_instructions_source}"
            ) from exc

        prompt_body = _strip_leading_yaml_front_matter(raw)
        if args.use_first_fenced_block:
            fenced = _extract_first_fenced_block(prompt_body)
            text = fenced if fenced is not None else prompt_body.strip()
        else:
            text = prompt_body.strip()
        if not text:
            raise ValueError(f"Prompt instructions file is empty: {prompt_instructions_source}")
        return text

    if args.prompt and args.prompt.strip():
        return args.prompt.strip()

    return DEFAULT_USER_PROMPT


def build_request_body(
    model: str,
    prompt_instructions: str,
    prompt_input: str,
    temperature: float,
    top_p: float,
    max_output_tokens: int | None,
) -> dict[str, Any]:
    user_text = json.dumps(
        {
            "prompt_instructions": prompt_instructions,
            "prompt_input": prompt_input,
        },
        indent=2,
        ensure_ascii=False,
    )
    system_prompt_text = SYSTEM_PROMPT.strip()

    # Default behavior: omit system role when empty to avoid implicit instructions.
    # Revert by always appending this item regardless of system_prompt_text content.
    input_items: list[dict[str, Any]] = []
    if system_prompt_text:
        input_items.append(
            {
                "role": "system",
                "content": [{"type": "input_text", "text": system_prompt_text}],
            }
        )
    input_items.append(
        {
            "role": "user",
            "content": [{"type": "input_text", "text": user_text}],
        }
    )

    body: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "top_p": top_p,
        "input": input_items,
    }

    if max_output_tokens is not None:
        body["max_output_tokens"] = max_output_tokens

    return body


def resolve_output_file_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path, Path]:
    """Resolve output file paths for extracted JSON, metadata JSON, full JSON, CSV, and Markdown."""
    prompt_instructions_source = args.prompt_instructions_file
    stem = (
        args.output_file_stem
        if args.output_file_stem
        else (
            prompt_instructions_source.stem
            if prompt_instructions_source
            else "invoke_chatgpt_API"
        )
    )

    if args.output_dir:
        output_dir = args.output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        extracted_json_path = output_dir / f"{stem}_output.json"
        metadata_json_path = output_dir / f"{stem}_run_metadata.json"
        full_api_json_path = output_dir / f"{stem}_api_response.json"
        csv_path = output_dir / f"{stem}_output.csv"
        md_path = output_dir / f"{stem}_output.md"
        return extracted_json_path, metadata_json_path, full_api_json_path, csv_path, md_path

    if prompt_instructions_source:
        prompt_dir = prompt_instructions_source.resolve().parent
        extracted_json_path = prompt_dir / f"{stem}_output.json"
        metadata_json_path = prompt_dir / f"{stem}_run_metadata.json"
        full_api_json_path = prompt_dir / f"{stem}_api_response.json"
        csv_path = prompt_dir / f"{stem}_output.csv"
        md_path = prompt_dir / f"{stem}_output.md"
        return extracted_json_path, metadata_json_path, full_api_json_path, csv_path, md_path

    script_dir = Path(__file__).resolve().parent
    extracted_json_path = script_dir / f"{stem}_output.json"
    metadata_json_path = script_dir / f"{stem}_run_metadata.json"
    full_api_json_path = script_dir / f"{stem}_api_response.json"
    csv_path = script_dir / f"{stem}_output.csv"
    md_path = script_dir / f"{stem}_output.md"
    return extracted_json_path, metadata_json_path, full_api_json_path, csv_path, md_path


def build_run_metadata_payload(
    args: argparse.Namespace,
    body: dict[str, Any],
    response_obj: dict[str, Any] | None,
    generated_at_utc: str,
    elapsed_s: float,
    written_files: dict[str, Path],
) -> dict[str, Any]:
    response_model = response_obj.get("model") if isinstance(response_obj, dict) else None
    system_fingerprint = (
        response_obj.get("system_fingerprint") if isinstance(response_obj, dict) else None
    )
    usage = response_obj.get("usage") if isinstance(response_obj, dict) else None
    response_id = response_obj.get("id") if isinstance(response_obj, dict) else None
    incomplete_details = response_obj.get("incomplete_details") if isinstance(response_obj, dict) else None
    output_count = len(response_obj.get("output") or []) if isinstance(response_obj, dict) else None
    metadata: dict[str, Any] = {
        "generated_at_utc": generated_at_utc,
        "runner": {
            "script_path": str(Path(__file__).resolve()),
            "api_base_url": API_BASE_URL,
            "timeout_seconds": args.timeout_seconds,
            "elapsed_seconds": round(elapsed_s, 3),
            "dry_run": bool(args.dry_run),
            "save_full_api_response": bool(args.save_full_api_response),
        },
        "request": {
            "model_requested": body.get("model"),
            "temperature": body.get("temperature"),
            "top_p": body.get("top_p"),
            "max_output_tokens": body.get("max_output_tokens"),
            "prompt_instructions_source": _prompt_instructions_source_label(args),
            "prompt_input_source": _prompt_input_source_label(args),
            "prompt_instructions_path": (
                str(args.prompt_instructions_file.resolve()) if args.prompt_instructions_file else None
            ),
            "prompt_input_path": str(args.prompt_input_file.resolve()) if args.prompt_input_file else None,
            "use_first_fenced_block": bool(args.use_first_fenced_block),
        },
        "response": {
            "id": response_id,
            "model_reported": response_model,
            "system_fingerprint": system_fingerprint,
            "usage": usage,
            "incomplete_details": incomplete_details,
            "output_item_count": output_count,
        },
        "artifacts": {name: str(path) for name, path in written_files.items()},
    }
    if ORGANIZATION_ID and not ORGANIZATION_ID.startswith("YOUR_"):
        metadata["runner"]["organization_id"] = ORGANIZATION_ID
    if PROJECT_ID and not PROJECT_ID.startswith("YOUR_"):
        metadata["runner"]["project_id"] = PROJECT_ID
    return metadata


def write_run_metadata_output_file(metadata_output_path: Path, metadata: dict[str, Any]) -> None:
    """Write execution metadata sidecar for the current runner invocation."""
    metadata_output_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_extracted_json_output_file(json_output_path: Path, text: str) -> None:
    """Write extracted output text JSON payload."""
    json_output_path.write_text(
        json.dumps({"extracted_output_text": text or ""}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_full_api_response_json_output_file(
    full_api_json_output_path: Path,
    response_obj: dict[str, Any],
) -> None:
    """Write full raw API response JSON payload."""
    full_api_json_output_path.write_text(
        json.dumps(response_obj, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def write_csv_output_file(csv_output_path: Path, text: str) -> None:
    """Write CSV derived from extracted text (table parse or single output_text cell)."""

    parsed_rows: list[list[str]] = []
    try:
        parsed_rows = list(csv.reader(io.StringIO(text or "")))
    except csv.Error:
        parsed_rows = []

    looks_like_csv_table = bool(parsed_rows) and len(parsed_rows[0]) > 1

    # Write CSV as UTF-8 with BOM for better Excel compatibility.
    with csv_output_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.writer(csv_file)

        if looks_like_csv_table:
            header = parsed_rows[0]
            if "evaluation_notes" in header:
                note_index = header.index("evaluation_notes")
                for row in parsed_rows[1:]:
                    if note_index < len(row):
                        note = row[note_index]
                        if len(note) >= 2 and note.startswith('"') and note.endswith('"'):
                            row[note_index] = note[1:-1]
            writer.writerows(parsed_rows)
        else:
            writer.writerow(["output_text"])
            writer.writerow([text or ""])


def _quote_yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _prompt_instructions_source_label(args: argparse.Namespace) -> str:
    if args.prompt_instructions_file:
        return "prompt_instructions_file"
    if args.prompt:
        return "prompt"
    return "default"


def _prompt_input_source_label(args: argparse.Namespace) -> str:
    if args.prompt_input_file:
        return "prompt_input_file"
    if args.prompt_input_json:
        return "prompt_input_json"
    return "default"


def _render_markdown_front_matter(
    args: argparse.Namespace,
    prompt_instructions: str,
    prompt_input: str,
    generated_at_utc: str,
) -> str:
    prompt_lines = prompt_instructions.splitlines() or [""]
    lines: list[str] = [
        "---",
        f"generated_at_utc: {_quote_yaml_string(generated_at_utc)}",
        "prompt_instructions:",
        f"  source: {_quote_yaml_string(_prompt_instructions_source_label(args))}",
    ]

    if args.prompt_instructions_file:
        lines.append(f"  path: {_quote_yaml_string(str(args.prompt_instructions_file.resolve()))}")

    lines.append("  text: |-")
    lines.extend(f"    {line}" for line in prompt_lines)

    lines.extend(
        [
            "prompt_input:",
            f"  source: {_quote_yaml_string(_prompt_input_source_label(args))}",
        ]
    )

    if args.prompt_input_file:
        lines.append(f"  path: {_quote_yaml_string(str(args.prompt_input_file.resolve()))}")

    lines.append("---")
    return "\n".join(lines)


def write_markdown_output_file(
    markdown_output_path: Path,
    text: str,
    args: argparse.Namespace,
    prompt_instructions: str,
    prompt_input: str,
    generated_at_utc: str,
) -> None:
    """Write extracted text to Markdown with YAML source metadata front matter."""
    front_matter = _render_markdown_front_matter(
        args=args,
        prompt_instructions=prompt_instructions,
        prompt_input=prompt_input,
        generated_at_utc=generated_at_utc,
    )
    body = text or ""
    markdown_output_path.write_text(f"{front_matter}\n\n{body}", encoding="utf-8")


def resolve_requested_output_formats(output_formats: list[str] | None) -> set[str]:
    """Return selected output formats, defaulting to JSON + CSV."""
    if not output_formats:
        return {"json", "csv"}
    return set(output_formats)


def write_requested_output_files(
    output_formats: set[str],
    extracted_json_output_path: Path,
    csv_output_path: Path,
    markdown_output_path: Path,
    text: str,
    args: argparse.Namespace,
    prompt_instructions: str,
    prompt_input: str,
    generated_at_utc: str,
) -> dict[str, Path]:
    """Write requested output artifact(s) and return their paths keyed by format."""
    written_files: dict[str, Path] = {}

    if "json" in output_formats:
        write_extracted_json_output_file(extracted_json_output_path, text)
        written_files["json"] = extracted_json_output_path

    if "csv" in output_formats:
        write_csv_output_file(csv_output_path, text)
        written_files["csv"] = csv_output_path

    if "md" in output_formats:
        write_markdown_output_file(
            markdown_output_path=markdown_output_path,
            text=text,
            args=args,
            prompt_instructions=prompt_instructions,
            prompt_input=prompt_input,
            generated_at_utc=generated_at_utc,
        )
        written_files["md"] = markdown_output_path

    return written_files


def extract_output_text(response_obj: dict[str, Any]) -> str:
    output_text = response_obj.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    chunks: list[str] = []
    for item in response_obj.get("output", []) or []:
        for content in item.get("content", []) or []:
            text = content.get("text")
            if isinstance(text, str) and text:
                chunks.append(text)
    return "\n".join(chunks).strip()


def get_incomplete_reason(response_obj: dict[str, Any]) -> str | None:
    """Return incomplete reason from Responses API payload, if present."""
    details = response_obj.get("incomplete_details")
    if isinstance(details, dict):
        reason = details.get("reason")
        if isinstance(reason, str) and reason.strip():
            return reason.strip()
    return None


def is_platform_limit_reason(reason: str | None) -> bool:
    """Best-effort check for token/platform limit style truncation reasons."""
    if not reason:
        return False
    normalized = reason.lower()
    return any(
        token in normalized
        for token in [
            "max_output_tokens",
            "max_tokens",
            "context_length",
            "length",
        ]
    )


def invoke_chatgpt(body: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    if not API_KEY:
        raise ValueError("API key file is missing/empty: secrets/openai_api_key.txt")
    if timeout_seconds <= 0:
        raise ValueError("--timeout-seconds must be a positive integer")

    url = f"{API_BASE_URL}/responses"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    if ORGANIZATION_ID and not ORGANIZATION_ID.startswith("YOUR_"):
        headers["OpenAI-Organization"] = ORGANIZATION_ID
    if PROJECT_ID and not PROJECT_ID.startswith("YOUR_"):
        headers["OpenAI-Project"] = PROJECT_ID

    data = json.dumps(body).encode("utf-8")
    req = Request(url, data=data, headers=headers, method="POST")

    try:
        with urlopen(req, timeout=timeout_seconds) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {error_body}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error: {exc}") from exc


def main() -> int:
    start_ts = time.perf_counter()
    args = parse_args()
    print(f"Invoking LLM prompt via API call.")
    print(f"Request timeout set to: {args.timeout_seconds} seconds. Waiting.")

    try:
        prompt_instructions = load_prompt_instructions(args)
        prompt_input = load_prompt_input(args)
        body = build_request_body(
            model=args.model,
            prompt_instructions=prompt_instructions,
            prompt_input=prompt_input,
            temperature=args.temperature,
            top_p=args.top_p,
            max_output_tokens=args.max_output_tokens,
        )
        if args.verbose:
            print("=== VERBOSE: REQUEST BODY ===")
            print(json.dumps(body, indent=2, ensure_ascii=False))
            user_text = ""
            for item in body.get("input", []):
                if isinstance(item, dict) and item.get("role") == "user":
                    for content in item.get("content", []):
                        if isinstance(content, dict) and content.get("type") == "input_text":
                            text = content.get("text")
                            if isinstance(text, str):
                                user_text = text
                                break
                    break
            print("=== VERBOSE: INPUT DIAGNOSTICS ===")
            print(f"prompt_instructions_chars: {len(prompt_instructions)}")
            print(f"prompt_input_chars: {len(prompt_input)}")
            print(f"user_message_chars: {len(user_text)}")
            print(
                "prompt_input_field_in_user_message: "
                f"{'\"prompt_input\"' in user_text}"
            )
        requested_formats = resolve_requested_output_formats(args.output_format)
        generated_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

        if args.dry_run:
            print("=== DRY RUN: RESOLVED PROMPT INSTRUCTIONS ===")
            print(prompt_instructions)
            print("\n=== DRY RUN: RESOLVED PROMPT INPUT ===")
            print(prompt_input)
            print("\n=== DRY RUN: REQUEST BODY ===")
            print(json.dumps(body, indent=2, ensure_ascii=False))
            if "md" in requested_formats:
                print("\n=== DRY RUN: MARKDOWN YAML FRONT MATTER PREVIEW ===")
                print(
                    _render_markdown_front_matter(
                        args=args,
                        prompt_instructions=prompt_instructions,
                        prompt_input=prompt_input,
                        generated_at_utc=generated_at_utc,
                    )
                )
            elapsed_s = time.perf_counter() - start_ts
            print(f"Total running time: {elapsed_s:.2f} seconds")
            return 0

        response_obj = invoke_chatgpt(body, args.timeout_seconds)
        text = extract_output_text(response_obj)
        incomplete_reason = get_incomplete_reason(response_obj)

        (
            extracted_json_output_path,
            metadata_json_output_path,
            full_api_json_output_path,
            csv_output_path,
            markdown_output_path,
        ) = resolve_output_file_paths(args)
        written_files = write_requested_output_files(
            output_formats=requested_formats,
            extracted_json_output_path=extracted_json_output_path,
            csv_output_path=csv_output_path,
            markdown_output_path=markdown_output_path,
            text=text,
            args=args,
            prompt_instructions=prompt_instructions,
            prompt_input=prompt_input,
            generated_at_utc=generated_at_utc,
        )
        elapsed_s = time.perf_counter() - start_ts
        run_metadata = build_run_metadata_payload(
            args=args,
            body=body,
            response_obj=response_obj,
            generated_at_utc=generated_at_utc,
            elapsed_s=elapsed_s,
            written_files=written_files,
        )
        write_run_metadata_output_file(metadata_json_output_path, run_metadata)
        written_files["run_metadata"] = metadata_json_output_path

        if args.save_full_api_response:
            write_full_api_response_json_output_file(full_api_json_output_path, response_obj)
            written_files["full_api_response"] = full_api_json_output_path

        if "json" in written_files:
            print(f"Extracted output JSON written to: {written_files['json']}")
        if "csv" in written_files:
            print(f"CSV output written to: {written_files['csv']}")
        if "md" in written_files:
            print(f"Markdown output written to: {written_files['md']}")
        if "run_metadata" in written_files:
            print(f"Run metadata JSON written to: {written_files['run_metadata']}")
        if args.save_full_api_response:
            print(f"Full API response JSON written to: {full_api_json_output_path}")
        if is_platform_limit_reason(incomplete_reason):
            print(
                "Notice: response is incomplete due to a platform/model token limit "
                f"(reason: {incomplete_reason})."
            )
        print(f"Total running time: {elapsed_s:.2f} seconds")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
