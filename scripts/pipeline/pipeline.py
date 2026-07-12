#!/usr/bin/env python3
"""First end-to-end Creative Studio pipeline for one image.

This module orchestrates existing components only: OpenAI Vision Adapter,
Concept Generator prompt, and Concept Card parser. It owns no analysis or
rendering logic itself.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parents[1]
OPENAI_DIR = PROJECT_ROOT / "scripts" / "openai"
GENERATOR_DIR = PROJECT_ROOT / "scripts" / "concept_generator"

# Existing modules are standalone scripts, so expose their directories without
# changing their import contracts.
sys.path.insert(0, str(OPENAI_DIR))
sys.path.insert(0, str(GENERATOR_DIR))

from client import (  # noqa: E402
    EmptyVisionResponseError,
    OpenAIVisionClient,
    VisionAdapterError,
)
from config import ConfigurationError  # noqa: E402
from parser import next_concept_id, save_concept_card  # noqa: E402


PROMPT_PATH = GENERATOR_DIR / "prompt.md"
CONCEPTS_DIR = PROJECT_ROOT / "brain" / "concepts"


class PipelineError(RuntimeError):
    """Raised when an orchestration step cannot safely continue."""


class VisionClient(Protocol):
    """Minimal adapter contract used by the pipeline."""

    def analyze_image(self, image_path: str | Path, prompt: str) -> dict[str, Any]: ...


@dataclass(frozen=True)
class PipelineResult:
    concept_id: str
    concept_path: Path


def load_prompt(prompt_path: Path = PROMPT_PATH) -> str:
    """Read the versioned Concept Generator prompt without modifying it."""
    try:
        prompt = prompt_path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        raise PipelineError(f"Concept Generator prompt not found: {prompt_path}") from error
    if not prompt.strip():
        raise PipelineError(f"Concept Generator prompt is empty: {prompt_path}")
    return prompt


def run_pipeline(
    image_path: str | Path,
    vision_client: VisionClient | None = None,
    prompt_path: Path = PROMPT_PATH,
    concepts_dir: Path = CONCEPTS_DIR,
) -> PipelineResult:
    """Analyse one image and create one new Concept Card.

    The Vision Adapter handles API and empty-text failures. The pipeline still
    guards against an empty mapping before passing the result to the parser.
    """
    source_image = Path(image_path).expanduser().resolve()
    prompt = load_prompt(prompt_path)
    client = vision_client or OpenAIVisionClient()

    try:
        model_response = client.analyze_image(source_image, prompt)
    except EmptyVisionResponseError as error:
        raise PipelineError("Model returned an empty response; no Concept Card was created.") from error
    except VisionAdapterError as error:
        raise PipelineError(f"Vision analysis failed: {error}") from error

    if not model_response:
        raise PipelineError("Model returned an empty response; no Concept Card was created.")
    if not isinstance(model_response, dict):
        raise PipelineError("Model response must be a structured JSON object.")

    concept_id = f"CC-{next_concept_id(concepts_dir):04d}"
    try:
        concept_path = save_concept_card(
            model_response=model_response,
            concept_id=concept_id,
            image_path=source_image,
            concepts_dir=concepts_dir,
        )
    except (FileExistsError, ValueError) as error:
        raise PipelineError(f"Concept Card was not created: {error}") from error

    return PipelineResult(concept_id=concept_id, concept_path=concept_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyse one image and create a draft Creative Concept Card."
    )
    parser.add_argument("image", type=Path, help="Path to one supported image file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = run_pipeline(args.image)
    except ConfigurationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    except PipelineError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("SUCCESS")
    print(f"ID: {result.concept_id}")
    print(f"Path: {result.concept_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
