#!/usr/bin/env python3
"""Forward Layer 1 scoring invocations to the shared prompt runner.

This wrapper exists so the scoring phase can grow its own orchestration logic
without requiring immediate changes to the just recipes. The initial version is
intentionally thin: it forwards every received CLI argument to
invoke_chatgpt_API.py and exits with the same status code.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def resolve_runner_path() -> Path:
	current_file = Path(__file__).resolve()
	repo_root = current_file.parents[3]
	runner_path = repo_root / "01_units/apps/prompt_runners/invoke_chatgpt_API.py"
	if not runner_path.is_file():
		raise FileNotFoundError(f"Prompt runner not found: {runner_path}")
	return runner_path


def main() -> int:
	try:
		runner_path = resolve_runner_path()
	except FileNotFoundError as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1

	command = [sys.executable, str(runner_path), *sys.argv[1:]]
	completed = subprocess.run(command, check=False)
	return completed.returncode


if __name__ == "__main__":
	raise SystemExit(main())