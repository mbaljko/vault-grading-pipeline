#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = next(
    (candidate for candidate in [SCRIPT_DIR, *SCRIPT_DIR.parents] if (candidate / ".git").exists()),
    None,
)
RUNNER_SCRIPT_RELATIVE = Path("01_units/apps/prompt_runners/invoke_chatgpt_API.py")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run prompt-driven segmentation through the shared LLM runner."
    )
    parser.add_argument("--input-path", type=Path, required=True, help="Source file for segmentation input.")
    parser.add_argument("--output-path", type=Path, required=True, help="Destination markdown file for runner output.")
    parser.add_argument(
        "--runner-prompt-path",
        type=Path,
        required=True,
        help="Prompt instructions file passed through to the shared LLM runner.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature forwarded to invoke_chatgpt_API.py.",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=1.0,
        help="Top-p value forwarded to invoke_chatgpt_API.py.",
    )
    parser.add_argument(
        "--runner-dry-run",
        action="store_true",
        help="Forward --dry-run to invoke_chatgpt_API.py.",
    )
    return parser.parse_args()


def derive_runner_stem(output_path: Path) -> str:
    stem = output_path.stem
    if stem.endswith("_output"):
        return stem[:-7]
    return stem


def main() -> int:
    args = parse_args()
    if REPO_ROOT is None:
        raise RuntimeError("Could not locate repository root from script path.")

    runner_script = REPO_ROOT / RUNNER_SCRIPT_RELATIVE
    input_path = args.input_path.resolve()
    output_path = args.output_path.resolve()
    runner_prompt_path = args.runner_prompt_path.resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if not runner_prompt_path.exists():
        raise FileNotFoundError(f"Runner prompt file not found: {runner_prompt_path}")
    if not runner_script.exists():
        raise FileNotFoundError(f"Runner script not found: {runner_script}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    runner_stem = derive_runner_stem(output_path)
    runner_output_path = output_path.parent / f"{runner_stem}_output.md"

    cmd = [
        sys.executable,
        str(runner_script),
        "--output-format",
        "md",
        "--output-dir",
        str(output_path.parent),
        "--prompt-instructions-file",
        str(runner_prompt_path),
        "--prompt-input-file",
        str(input_path),
        "--output-file-stem",
        runner_stem,
        "--temperature",
        str(args.temperature),
        "--top-p",
        str(args.top_p),
    ]
    if args.runner_dry_run:
        cmd.append("--dry-run")

    subprocess.run(cmd, check=True)

    if args.runner_dry_run:
        return 0
    if not runner_output_path.exists():
        raise FileNotFoundError(f"Expected runner output not found: {runner_output_path}")
    if runner_output_path != output_path:
        shutil.move(str(runner_output_path), str(output_path))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())