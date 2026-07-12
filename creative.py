#!/usr/bin/env python3
"""Unified local command-line entry point for Creative Studio."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
QUEUE_DIR = PROJECT_ROOT / "scripts" / "queue"
SEARCH_DIR = PROJECT_ROOT / "brain" / "search"
INSIGHTS_DIR = PROJECT_ROOT / "brain" / "insights"
GENERATOR_DIR = PROJECT_ROOT / "brain" / "generator"
OPENAI_DIR = PROJECT_ROOT / "scripts" / "openai"
PIPELINE_DIR = PROJECT_ROOT / "scripts" / "pipeline"
DIRECTOR_DIR = PROJECT_ROOT / "agents" / "creative_director"
REFERENCE_DIR = PROJECT_ROOT / "assets" / "references"
MANUAL_ANALYSIS_DIR = PROJECT_ROOT / "brain" / "manual-analysis"
GENERATED_DIR = PROJECT_ROOT / "brain" / "generated"

for module_dir in [QUEUE_DIR, SEARCH_DIR, INSIGHTS_DIR, GENERATOR_DIR, OPENAI_DIR, PIPELINE_DIR, DIRECTOR_DIR]:
    sys.path.insert(0, str(module_dir))

from config import ConfigurationError, load_dotenv  # noqa: E402
from director import create_and_save_plan  # noqa: E402
from generator import generate_cards  # noqa: E402
from index import library_statistics, load_cards  # noqa: E402
from insights import build_report  # noqa: E402
from queue import DEFAULT_QUEUE_DIR, STATUSES, image_files, load_records, scan  # noqa: E402


def queue_status() -> dict[str, int]:
    """Count records in every existing queue status without changing the queue."""
    counts = Counter(str(record.get("status", "unknown")) for record in load_records(DEFAULT_QUEUE_DIR))
    return {status: counts[status] for status in STATUSES}


def reference_image_count() -> int:
    return sum(1 for _ in image_files(REFERENCE_DIR))


def module_states(key_configured: bool) -> dict[str, str]:
    """Report availability only; no module action is performed here."""
    return {
        "queue": "ready" if (QUEUE_DIR / "queue.py").is_file() else "missing",
        "brain_search": "ready" if (SEARCH_DIR / "index.py").is_file() else "missing",
        "insights": "ready" if (INSIGHTS_DIR / "insights.py").is_file() else "missing",
        "generator": "ready" if (GENERATOR_DIR / "generator.py").is_file() else "missing",
        "vision_adapter": "configured" if key_configured else "API key missing",
        "pipeline": "ready" if (PIPELINE_DIR / "pipeline.py").is_file() else "missing",
    }


def command_status(_: argparse.Namespace) -> int:
    load_dotenv()
    key_configured = bool(os.getenv("OPENAI_API_KEY", "").strip())
    cards = load_cards()
    report = {
        "reference_images": reference_image_count(),
        "concept_cards": len(cards),
        "manual_json_analyses": len(list(MANUAL_ANALYSIS_DIR.glob("*.json"))),
        "generated_cards": len(list(GENERATED_DIR.glob("CG-*.md"))),
        "queue": queue_status(),
        "env_file": (PROJECT_ROOT / ".env").is_file(),
        "openai_api_key_configured": key_configured,
        "modules": module_states(key_configured),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def command_scan(_: argparse.Namespace) -> int:
    found = reference_image_count()
    created = scan()
    report = {
        "images_found": found,
        "new_queue_records": len(created),
        "duplicates_skipped": max(found - len(created), 0),
        "queue": queue_status(),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def command_brain(_: argparse.Namespace) -> int:
    print(json.dumps(library_statistics(load_cards()), ensure_ascii=False, indent=2))
    return 0


def command_insights(_: argparse.Namespace) -> int:
    print(json.dumps(build_report(load_cards()), ensure_ascii=False, indent=2))
    return 0


def command_generate(args: argparse.Namespace) -> int:
    generated = generate_cards(
        load_cards(), count=args.count, geo=args.geo, funnel=args.funnel
    )
    report = {
        "created": len(generated),
        "most_novel": [
            {"id": item.concept_id, "novelty_score": item.novelty_score}
            for item in sorted(generated, key=lambda item: -item.novelty_score)[:3]
        ],
        "most_similar": [
            {"id": item.concept_id, "similarity_to_existing": item.similarity_to_existing}
            for item in sorted(
                generated, key=lambda item: -item.similarity_to_existing["score"]
            )[:3]
        ],
        "send_to_design_first": [
            item.concept_id
            for item in sorted(
                generated,
                key=lambda item: (-item.novelty_score, item.risk_score, item.concept_id),
            )[:3]
        ],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def command_plan(args: argparse.Namespace) -> int:
    plan = create_and_save_plan(
        geo=args.geo,
        funnel=args.funnel,
        count=args.count,
        task=args.task,
    )
    print("PLAN CREATED")
    print(f"Path: {plan.path.relative_to(PROJECT_ROOT)}")
    print(f"Hypotheses: {plan.hypotheses}")
    return 0


def command_analyze(args: argparse.Namespace) -> int:
    """Run the existing paid pipeline only after explicit CLI invocation."""
    from pipeline import PipelineError, run_pipeline  # noqa: E402

    try:
        result = run_pipeline(args.image)
    except ConfigurationError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    except PipelineError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        if error.raw_response is not None:
            print("FULL MODEL RESPONSE:", file=sys.stderr)
            print(error.raw_response, file=sys.stderr)
        if error.log_path is not None:
            print(f"ERROR LOG: {error.log_path.relative_to(PROJECT_ROOT)}", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"ERROR: Analysis could not be completed: {error}", file=sys.stderr)
        return 1

    response_json = getattr(result, "response_json_path", None)
    print("SUCCESS")
    print(f"ID: {result.concept_id}")
    print(f"Path: {result.concept_path.relative_to(PROJECT_ROOT)}")
    print(f"Filled fields: {getattr(result, 'filled_fields', 'unavailable')}")
    print(f"Analysis time: {getattr(result, 'analysis_seconds', 0):.2f}s")
    if response_json is not None:
        print(f"JSON: {response_json.relative_to(PROJECT_ROOT)}")
    usage = getattr(result, "usage", None) or {}
    print(f"Cost: {usage.get('cost', 'unavailable')}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unified local CLI for Creative Studio.",
        epilog=(
            "Examples:\n"
            "  python3 creative.py status\n"
            "  python3 creative.py generate --count 10 --geo TR --funnel registration\n"
            "  python3 creative.py analyze \"assets/references/example.png\""
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="Show local project status.").set_defaults(handler=command_status)
    commands.add_parser("scan", help="Queue new reference images.").set_defaults(handler=command_scan)
    commands.add_parser("brain", help="Show Creative Brain statistics.").set_defaults(handler=command_brain)
    commands.add_parser("insights", help="Show the local Insights report.").set_defaults(handler=command_insights)
    generate = commands.add_parser("generate", help="Generate local Concept Card drafts.")
    generate.add_argument("--count", type=int, default=20, help="Number of drafts to create.")
    generate.add_argument("--geo", choices=("TR", "AZ"), help="Restrict drafts to one GEO.")
    generate.add_argument(
        "--funnel", choices=("registration", "lead"), help="Restrict drafts to one funnel."
    )
    generate.set_defaults(handler=command_generate)
    plan = commands.add_parser("plan", help="Create a local Creative Director plan.")
    plan.add_argument("--geo", choices=("TR", "AZ"), required=True)
    plan.add_argument("--funnel", choices=("registration", "lead"), required=True)
    plan.add_argument("--count", type=int, default=20)
    plan.add_argument("--task", help="Optional user task text for the plan goal.")
    plan.set_defaults(handler=command_plan)
    analyze = commands.add_parser("analyze", help="Run the explicit paid single-image pipeline.")
    analyze.add_argument("image", type=Path, help="Path to one image.")
    analyze.set_defaults(handler=command_analyze)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.handler(args)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
