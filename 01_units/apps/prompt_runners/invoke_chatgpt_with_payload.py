#!/usr/bin/env python3
"""Invoke ChatGPT API with a prompt and JSON payload.

Set environment variables, then run this script with either:
- --payload-file path/to/payload.json, or
- --payload-json '{"key": "value"}'

Prompt can be provided via:
- --prompt-path /full/path/to/prompt.md
- --prompt-file path/to/prompt.txt
- --prompt "..."

If neither prompt option is provided, a built-in default prompt is used.
If neither payload option is provided, a built-in sample payload is used.

Optional env vars:
- OPENAI_ORG_ID
- OPENAI_PROJECT_ID
- OPENAI_MODEL
- OPENAI_API_BASE_URL
- OPENAI_SYSTEM_PROMPT

API key source (exclusive):
- repository-root `secrets/openai_api_key.txt`

Example:
    python invoke_chatgpt_with_payload.py \
      --prompt "Summarize this calibration payload" \
      --payload-file payload.json

On successful API calls, output is written to both JSON and CSV files and the
resolved file paths are printed to stdout.

Output location behavior:
- If --prompt-path or --prompt-file is provided, output files are written next
    to that prompt file as:
    - <prompt_stem>_output.json
    - <prompt_stem>_output.csv
- If no prompt file/path is provided, output files are written next to this
    script as:
    - invoke_chatgpt_with_payload_output.json
    - invoke_chatgpt_with_payload_output.csv

Output paths are based on resolved absolute paths and do not depend on the
current working directory used to invoke the script.
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


def resolve_output_file_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    """Resolve output file paths for raw JSON and companion CSV."""
    prompt_source = args.prompt_path or args.prompt_file
    if prompt_source:
        base = prompt_source.resolve().with_name(f"{prompt_source.stem}_output")
        return base.with_suffix(".json"), base.with_suffix(".csv")

    base = Path(__file__).resolve().with_name("invoke_chatgpt_with_payload_output")
    return base.with_suffix(".json"), base.with_suffix(".csv")


def write_output_files(
    json_output_path: Path,
    csv_output_path: Path,
    text: str,
    response_obj: dict[str, Any],
) -> None:
    """Write response JSON + extracted text and companion CSV."""
    json_payload = dict(response_obj)
    json_payload["extracted_output_text"] = text or ""

    json_output_path.write_text(
        json.dumps(json_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

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
    print(f"Request timeout set to: {REQUEST_TIMEOUT_SECONDS} seconds")

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

        if args.dry_run:
            print("=== DRY RUN: RESOLVED PROMPT ===")
            print(prompt)
            print("\n=== DRY RUN: RESOLVED PAYLOAD ===")
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            print("\n=== DRY RUN: REQUEST BODY ===")
            print(json.dumps(body, indent=2, ensure_ascii=False))
            elapsed_s = time.perf_counter() - start_ts
            print(f"Total running time: {elapsed_s:.2f} seconds")
            return 0

        response_obj = invoke_chatgpt(body)
        text = extract_output_text(response_obj)
        incomplete_reason = get_incomplete_reason(response_obj)

        json_output_path, csv_output_path = resolve_output_file_paths(args)
        write_output_files(json_output_path, csv_output_path, text, response_obj)
        print(f"JSON output written to: {json_output_path}")
        print(f"CSV output written to: {csv_output_path}")
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
