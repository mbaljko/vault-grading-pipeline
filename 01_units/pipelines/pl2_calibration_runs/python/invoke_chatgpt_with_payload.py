#!/usr/bin/env python3
"""Invoke ChatGPT API with a prompt and JSON payload.

Set environment variables, then run this script with either:
- --payload-file path/to/payload.json, or
- --payload-json '{"key": "value"}'

Prompt can be provided via:
- --prompt-file path/to/prompt.txt
- --prompt "..."

If neither prompt option is provided, a built-in default prompt is used.
If neither payload option is provided, a built-in sample payload is used.

Required env var:
- OPENAI_API_KEY

Optional env vars:
- OPENAI_ORG_ID
- OPENAI_PROJECT_ID
- OPENAI_MODEL
- OPENAI_API_BASE_URL
- OPENAI_SYSTEM_PROMPT

Example:
    python invoke_chatgpt_with_payload.py \
      --prompt "Summarize this calibration payload" \
      --payload-file payload.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# ==============================
# Account / API configuration
# ==============================
API_KEY = os.getenv("OPENAI_API_KEY", "")
ORGANIZATION_ID = os.getenv("OPENAI_ORG_ID", "")
PROJECT_ID = os.getenv("OPENAI_PROJECT_ID", "")
MODEL = os.getenv("OPENAI_MODEL", "gpt-5.1")
API_BASE_URL = os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1")
SYSTEM_PROMPT = os.getenv("OPENAI_SYSTEM_PROMPT", "You are a helpful assistant.")
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
        "--prompt-file",
        type=Path,
        help="Path to a text file containing prompt text.",
    )
    parser.add_argument(
        "--payload-file",
        type=Path,
        help="Path to a JSON file payload.",
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
        default=1200,
        help="Maximum output tokens.",
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
            return json.loads(args.payload_file.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ValueError(f"Payload file not found: {args.payload_file}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Payload file is not valid JSON: {exc}") from exc

    try:
        return json.loads(args.payload_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"--payload-json is not valid JSON: {exc}") from exc


def load_prompt(args: argparse.Namespace) -> str:
    if args.prompt and args.prompt_file:
        raise ValueError("Provide at most one of --prompt or --prompt-file.")

    if args.prompt_file:
        try:
            text = args.prompt_file.read_text(encoding="utf-8").strip()
        except FileNotFoundError as exc:
            raise ValueError(f"Prompt file not found: {args.prompt_file}") from exc
        if not text:
            raise ValueError(f"Prompt file is empty: {args.prompt_file}")
        return text

    if args.prompt and args.prompt.strip():
        return args.prompt.strip()

    return DEFAULT_USER_PROMPT


def build_request_body(
    model: str,
    prompt: str,
    payload: dict[str, Any],
    temperature: float,
    max_output_tokens: int,
) -> dict[str, Any]:
    user_text = (
        f"Prompt:\n{prompt}\n\n"
        f"Payload (JSON):\n{json.dumps(payload, indent=2, ensure_ascii=False)}"
    )

    return {
        "model": model,
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
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


def invoke_chatgpt(body: dict[str, Any]) -> dict[str, Any]:
    if not API_KEY:
        raise ValueError("OPENAI_API_KEY is not set.")

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
        with urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {error_body}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error: {exc}") from exc


def main() -> int:
    args = parse_args()

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
            return 0

        response_obj = invoke_chatgpt(body)
        text = extract_output_text(response_obj)

        print("=== MODEL OUTPUT ===")
        print(text or "<no text output>")
        print("\n=== RAW RESPONSE (JSON) ===")
        print(json.dumps(response_obj, indent=2, ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
