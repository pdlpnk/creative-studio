#!/usr/bin/env python3
"""Designer Agent v1: turn a Creative Plan into image-generation prompts."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from prompt_builder import build_prompt, parse_creative_plan, prompt_filename


MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parents[1]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output" / "prompts"


@dataclass(frozen=True)
class DesignResult:
    plan_path: Path
    prompt_paths: list[Path]


def create_prompts(plan: Path | Any, output_dir: Path = DEFAULT_OUTPUT_DIR) -> DesignResult:
    """Create prompts from a plan path or a Director ``CreativePlan`` object.

    The Director object exposes ``path``; accepting it avoids duplicating or
    serialising the plan before Designer starts its local hand-off.
    """
    plan_path = Path(getattr(plan, "path", plan)).resolve()
    if not plan_path.is_file():
        raise FileNotFoundError(f"Creative Plan not found: {plan_path}")
    specs = parse_creative_plan(plan_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_paths: list[Path] = []
    for spec in specs:
        prompt_path = output_dir / prompt_filename(spec)
        prompt_path.write_text(build_prompt(spec), encoding="utf-8")
        prompt_paths.append(prompt_path)
    return DesignResult(plan_path=plan_path, prompt_paths=prompt_paths)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create local generation prompts from a Creative Plan.")
    parser.add_argument("plan", type=Path, help="Path to a Creative Director Markdown plan.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = create_prompts(args.plan, args.output_dir)
    print(f"PROMPTS CREATED: {len(result.prompt_paths)}")
    for prompt_path in result.prompt_paths:
        print(prompt_path.relative_to(PROJECT_ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
