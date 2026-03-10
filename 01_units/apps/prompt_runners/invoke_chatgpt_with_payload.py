#!/usr/bin/env python3
"""Send a prompt and payload to the OpenAI Responses API and persist results.

What this script does:
- Resolves prompt and payload inputs from CLI args or built-in defaults.
- Calls the OpenAI Responses API.
- Persists extracted output text in requested file formats.

Inputs:
- Prompt input (choose one):
    - `--prompt "..."`
    - `--prompt-file path/to/prompt.txt`
    - `--prompt-path /full/path/to/prompt.md`
- Payload input (choose one):
    - `--payload-json '{"key": "value"}'`
    - `--payload-file path/to/payload.txt`
- If no prompt is provided, a built-in default prompt is used.
- If no payload is provided, a built-in sample payload is used.

Outputs:
- The full API response object is always captured in memory.
- `extracted_output_text` is derived from that full API response object.
- `--output-format <json|csv|md>` (repeatable) selects which artifacts are written:
    - `json`: writes JSON containing `extracted_output_text`.
    - `csv`: writes CSV derived from `extracted_output_text`.
        - If text looks like CSV, rows are parsed and written.
        - Otherwise, a single-column CSV (`output_text`) is written.
    - `md`: writes Markdown with YAML front matter metadata (prompt, payload info, timestamp)
        followed by `extracted_output_text`.
- `--save-full-api-response` controls whether a separate raw API response JSON file is written.
- Output filename patterns:
    - Extracted JSON: `<stem>_output.json`
    - Full API response JSON (only when `--save-full-api-response` is set): `<stem>_api_response.json`
    - CSV: `<stem>_output.csv`
    - Markdown: `<stem>_output.md`
- `--output-file-stem <stem>` optionally overrides `<stem>` for all outputs.
- Output path behavior:
    - If `--output-dir` is provided, all outputs are written there.
    - Otherwise, when prompt file/path is provided, outputs are written next to that prompt file.
    - Otherwise, outputs are written next to this script file.
- Paths are resolved to absolute paths before writing.

Additional invocation parameters:
- `--temperature <float>`
- `--max-output-tokens <int>`
- `--model <name>`
- `--output-file-stem <stem>`
- `--save-full-api-response`
- `--dry-run`

Environment configuration:
- Optional env vars:
    - `OPENAI_ORG_ID`
    - `OPENAI_PROJECT_ID`
    - `OPENAI_MODEL`
    - `OPENAI_API_BASE_URL`
    - `OPENAI_SYSTEM_PROMPT`
- API key source (exclusive): `secrets/openai_api_key.txt` at repository root.

Example:
        python invoke_chatgpt_with_payload.py \
                --prompt "Summarize this calibration payload" \
                --payload-file payload.json
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
SYSTEM_PROMPT = os.getenv("OPENAI_SYSTEM_PROMPT", "You are a helpful assistant.")
REQUEST_TIMEOUT_SECONDS = 600
DEFAULT_USER_PROMPT = (
    "Analyze the provided text segments. Return concise themes, key claims, "
    "and any notable inconsistencies."
)
DEFAULT_PAYLOAD: dict[str, Any] = {
    "segments": [
        "Example segment A.",
        "Example segment B.",
    ]
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send prompt + payload to ChatGPT API.")
    parser.add_argument("--prompt", help="User prompt text.")
    parser.add_argument(
        "--prompt-path",
        type=Path,
        help=(
            "Full path to a Markdown file containing the prompt in a fenced block "
            "(``` or ````)."
        ),
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        help=(
            "Path to a text/Markdown file containing prompt text. If fenced Markdown "
            "blocks are present, the first fenced block is used."
        ),
    )
    parser.add_argument(
        "--payload-file",
        type=Path,
        help="Path to text/Markdown payload file (handled as text).",
    )
    parser.add_argument(
        "--payload-json",
        help="Inline JSON payload string.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Sampling temperature.",
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
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Optional output directory for generated files. If omitted, outputs are "
            "written next to the prompt file (when provided) or next to this script."
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
            "When omitted, stem is derived from prompt file/path or falls back "
            "to 'invoke_chatgpt_with_payload'."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved prompt/payload/request body and exit without calling API.",
    )
    return parser.parse_args()


def load_payload(args: argparse.Namespace) -> dict[str, Any]:
    if args.payload_file and args.payload_json:
        raise ValueError("Provide at most one of --payload-file or --payload-json.")

    if not args.payload_file and not args.payload_json:
        return DEFAULT_PAYLOAD

    if args.payload_file:
        try:
            raw = args.payload_file.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ValueError(f"Payload file not found: {args.payload_file}") from exc

        payload_text = _extract_first_fenced_block(raw) or raw.strip()
        if not payload_text:
            raise ValueError(f"Payload file is empty: {args.payload_file}")

        # --payload-file handler: always treat input as text content
        return {"segments": [payload_text.strip()]}

    try:
        return json.loads(args.payload_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"--payload-json is not valid JSON: {exc}") from exc


def load_prompt(args: argparse.Namespace) -> str:
    provided_count = sum(
        bool(x)
        for x in [
            args.prompt,
            args.prompt_file,
            args.prompt_path,
        ]
    )
    if provided_count > 1:
        raise ValueError("Provide at most one of --prompt, --prompt-file, or --prompt-path.")

    prompt_source = args.prompt_path or args.prompt_file

    if prompt_source:
        try:
            raw = prompt_source.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ValueError(f"Prompt file not found: {prompt_source}") from exc

        fenced = _extract_first_fenced_block(raw)
        text = fenced if fenced is not None else raw.strip()
        if not text:
            raise ValueError(f"Prompt file is empty or contains an empty fenced block: {prompt_source}")
        return text

    if args.prompt and args.prompt.strip():
        return args.prompt.strip()

    return DEFAULT_USER_PROMPT


def build_request_body(
    model: str,
    prompt: str,
    payload: dict[str, Any],
    temperature: float,
    max_output_tokens: int | None,
) -> dict[str, Any]:
    user_text = (
        f"Prompt:\n{prompt}\n\n"
        f"Payload (JSON):\n{json.dumps(payload, indent=2, ensure_ascii=False)}"
    )

    body: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "input": [
            {
                "role": "system",
                "content": [{"type": "input_text", "text": SYSTEM_PROMPT}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_text}],
            },
        ],
    }

    if max_output_tokens is not None:
        body["max_output_tokens"] = max_output_tokens

    return body


def resolve_output_file_paths(args: argparse.Namespace) -> tuple[Path, Path, Path, Path]:
    """Resolve output file paths for extracted JSON, full JSON, CSV, and Markdown."""
    prompt_source = args.prompt_path or args.prompt_file
    stem = (
        args.output_file_stem
        if args.output_file_stem
        else (prompt_source.stem if prompt_source else "invoke_chatgpt_with_payload")
    )

    if args.output_dir:
        output_dir = args.output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        extracted_json_path = output_dir / f"{stem}_output.json"
        full_api_json_path = output_dir / f"{stem}_api_response.json"
        csv_path = output_dir / f"{stem}_output.csv"
        md_path = output_dir / f"{stem}_output.md"
        return extracted_json_path, full_api_json_path, csv_path, md_path

    if prompt_source:
        prompt_dir = prompt_source.resolve().parent
        extracted_json_path = prompt_dir / f"{stem}_output.json"
        full_api_json_path = prompt_dir / f"{stem}_api_response.json"
        csv_path = prompt_dir / f"{stem}_output.csv"
        md_path = prompt_dir / f"{stem}_output.md"
        return extracted_json_path, full_api_json_path, csv_path, md_path

    script_dir = Path(__file__).resolve().parent
    extracted_json_path = script_dir / f"{stem}_output.json"
    full_api_json_path = script_dir / f"{stem}_api_response.json"
    csv_path = script_dir / f"{stem}_output.csv"
    md_path = script_dir / f"{stem}_output.md"
    return extracted_json_path, full_api_json_path, csv_path, md_path


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


def _prompt_source_label(args: argparse.Namespace) -> str:
    if args.prompt_path:
        return "prompt_path"
    if args.prompt_file:
        return "prompt_file"
    if args.prompt:
        return "prompt"
    return "default"


def _payload_source_label(args: argparse.Namespace) -> str:
    if args.payload_file:
        return "payload_file"
    if args.payload_json:
        return "payload_json"
    return "default"


def _render_markdown_front_matter(
    args: argparse.Namespace,
    prompt: str,
    payload: dict[str, Any],
    generated_at_utc: str,
) -> str:
    prompt_lines = prompt.splitlines() or [""]
    payload_keys = sorted(str(k) for k in payload.keys())
    segment_count = 0
    segments_value = payload.get("segments")
    if isinstance(segments_value, list):
        segment_count = len(segments_value)

    lines: list[str] = [
        "---",
        f"generated_at_utc: {_quote_yaml_string(generated_at_utc)}",
        "prompt:",
        f"  source: {_quote_yaml_string(_prompt_source_label(args))}",
    ]

    if args.prompt_path:
        lines.append(f"  path: {_quote_yaml_string(str(args.prompt_path.resolve()))}")
    elif args.prompt_file:
        lines.append(f"  path: {_quote_yaml_string(str(args.prompt_file.resolve()))}")

    lines.append("  text: |-")
    lines.extend(f"    {line}" for line in prompt_lines)

    lines.extend(
        [
            "payload:",
            f"  source: {_quote_yaml_string(_payload_source_label(args))}",
            f"  top_level_keys: [{', '.join(_quote_yaml_string(k) for k in payload_keys)}]",
            f"  segment_count: {segment_count}",
        ]
    )

    if args.payload_file:
        lines.append(f"  path: {_quote_yaml_string(str(args.payload_file.resolve()))}")

    lines.append("---")
    return "\n".join(lines)


def write_markdown_output_file(
    markdown_output_path: Path,
    text: str,
    args: argparse.Namespace,
    prompt: str,
    payload: dict[str, Any],
    generated_at_utc: str,
) -> None:
    """Write extracted text to Markdown with YAML source metadata front matter."""
    front_matter = _render_markdown_front_matter(
        args=args,
        prompt=prompt,
        payload=payload,
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
    prompt: str,
    payload: dict[str, Any],
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
            prompt=prompt,
            payload=payload,
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


def invoke_chatgpt(body: dict[str, Any]) -> dict[str, Any]:
    if not API_KEY:
        raise ValueError("API key file is missing/empty: secrets/openai_api_key.txt")

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
        with urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
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
    print(f"Request timeout set to: {REQUEST_TIMEOUT_SECONDS} seconds. Waiting.")

    try:
        prompt = load_prompt(args)
        payload = load_payload(args)
        body = build_request_body(
            model=args.model,
            prompt=prompt,
            payload=payload,
            temperature=args.temperature,
            max_output_tokens=args.max_output_tokens,
        )
        requested_formats = resolve_requested_output_formats(args.output_format)
        generated_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

        if args.dry_run:
            print("=== DRY RUN: RESOLVED PROMPT ===")
            print(prompt)
            print("\n=== DRY RUN: RESOLVED PAYLOAD ===")
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            print("\n=== DRY RUN: REQUEST BODY ===")
            print(json.dumps(body, indent=2, ensure_ascii=False))
            if "md" in requested_formats:
                print("\n=== DRY RUN: MARKDOWN YAML FRONT MATTER PREVIEW ===")
                print(
                    _render_markdown_front_matter(
                        args=args,
                        prompt=prompt,
                        payload=payload,
                        generated_at_utc=generated_at_utc,
                    )
                )
            elapsed_s = time.perf_counter() - start_ts
            print(f"Total running time: {elapsed_s:.2f} seconds")
            return 0

        response_obj = invoke_chatgpt(body)
        text = extract_output_text(response_obj)
        incomplete_reason = get_incomplete_reason(response_obj)

        (
            extracted_json_output_path,
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
            prompt=prompt,
            payload=payload,
            generated_at_utc=generated_at_utc,
        )

        if args.save_full_api_response:
            write_full_api_response_json_output_file(full_api_json_output_path, response_obj)

        if "json" in written_files:
            print(f"Extracted output JSON written to: {written_files['json']}")
        if "csv" in written_files:
            print(f"CSV output written to: {written_files['csv']}")
        if "md" in written_files:
            print(f"Markdown output written to: {written_files['md']}")
        if args.save_full_api_response:
            print(f"Full API response JSON written to: {full_api_json_output_path}")
        if is_platform_limit_reason(incomplete_reason):
            print(
                "Notice: response is incomplete due to a platform/model token limit "
                f"(reason: {incomplete_reason})."
            )
        elapsed_s = time.perf_counter() - start_ts
        print(f"Total running time: {elapsed_s:.2f} seconds")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
