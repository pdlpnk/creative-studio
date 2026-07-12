#!/usr/bin/env python3
"""Generate draft Concept Cards from one image or a folder of images.

Creative Concept Generator v1 intentionally uses a local MOCK provider.  The
``analyze_image`` boundary is the only component that needs replacing when an
OpenAI vision provider is introduced later.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from parser import next_concept_id, save_concept_card


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parents[1]
CONCEPTS_DIR = PROJECT_ROOT / "brain" / "concepts"
PROMPT_PATH = MODULE_DIR / "prompt.md"


def sha256_file(path: Path) -> str:
    """Return the SHA-256 checksum without loading an entire image in memory."""
    digest = hashlib.sha256()
    with path.open("rb") as image_file:
        for chunk in iter(lambda: image_file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def infer_context(image_path: Path) -> dict[str, str]:
    """Infer only reliable context from the reference-library directory layout."""
    parts = {part.lower() for part in image_path.parts}
    geo = "TR" if "tr" in parts else "AZ" if "az" in parts else "unknown"
    funnel = (
        "registration"
        if "registration" in parts
        else "lead"
        if "lead" in parts
        else "unknown"
    )
    return {"geo": geo, "funnel": funnel}


def analyze_image(image_path: Path) -> dict[str, Any]:
    """Return a deterministic MOCK response shaped like the future vision result.

    This function does not inspect pixels or send a network request.  It exists
    as the provider boundary that a future OpenAI Responses API implementation
    will replace while keeping the CLI and parser unchanged.
    """
    context = infer_context(image_path)
    return {
        "analysis_status": "pending_review",
        "general": {
            "filename": image_path.name,
            "hash": sha256_file(image_path),
            "date": datetime.fromtimestamp(
                image_path.stat().st_mtime, tz=timezone.utc
            ).isoformat(),
            "geo": context["geo"],
            "funnel": context["funnel"],
            "language": "unknown",
            "creative_type": "static image (mock analysis)",
        },
        "visual": {
            "primary_colors": [],
            "accent_colors": [],
            "background": "not analysed (mock)",
            "composition": "not analysed (mock)",
            "layout": "not analysed (mock)",
            "perspective": "unknown",
            "objects": [],
            "phone_present": False,
            "gift_present": False,
            "coins_present": False,
            "person_present": False,
            "icons": [],
            "cta_button": "unknown",
            "typography": "not analysed (mock)",
            "font_weight": "unknown",
            "contrast": "not analysed (mock)",
            "spacing": "not analysed (mock)",
            "visual_complexity": "unknown",
            "emotion": [],
        },
        "copy": {
            "headline": "",
            "subheadline": "",
            "offer": "",
            "cta": "",
            "numbers": [],
            "currency": [],
            "language_quality": "not analysed (mock)",
            "readability": "not analysed (mock)",
        },
        "marketing": {
            "audience": "not inferred (mock)",
            "pain": "",
            "desire": "",
            "hook": "",
            "trust_elements": [],
            "urgency": "none",
            "social_proof": "none",
            "value_proposition": "",
        },
        "design_score": {
            "composition": None,
            "readability": None,
            "contrast": None,
            "hierarchy": None,
            "cta_visibility": None,
            "offer_visibility": None,
            "overall": None,
        },
        "production_notes": {
            "why_it_may_work": "Requires image analysis and human review.",
            "weaknesses": "Requires image analysis and human review.",
            "what_to_test": "No recommendation until image analysis is enabled.",
            "what_to_change": "No recommendation until image analysis is enabled.",
            "what_to_keep": "No recommendation until image analysis is enabled.",
        },
    }


def collect_images(target: Path) -> Iterable[Path]:
    """Yield supported images from one path or recursively from one directory."""
    if target.is_file():
        if target.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported image extension: {target.suffix}")
        yield target
        return

    if target.is_dir():
        for path in sorted(target.rglob("*")):
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                yield path
        return

    raise FileNotFoundError(f"Input path does not exist: {target}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create draft Concept Cards using the local MOCK provider."
    )
    parser.add_argument("input", type=Path, help="An image file or a folder of images.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render and report cards without writing them to brain/concepts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input.expanduser().resolve()
    images = list(collect_images(input_path))
    if not images:
        print("No supported images found.", file=sys.stderr)
        return 1

    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    print(f"Loaded analysis prompt: {PROMPT_PATH.name} ({len(prompt)} characters)")

    next_id = next_concept_id(CONCEPTS_DIR)
    for offset, image_path in enumerate(images):
        concept_id = f"CC-{next_id + offset:04d}"
        response = analyze_image(image_path)
        if args.dry_run:
            print(f"DRY RUN: {image_path} -> {CONCEPTS_DIR / (concept_id + '.md')}")
            continue

        output_path = save_concept_card(
            model_response=response,
            concept_id=concept_id,
            image_path=image_path,
            concepts_dir=CONCEPTS_DIR,
        )
        print(f"Created {output_path.relative_to(PROJECT_ROOT)}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(2)
