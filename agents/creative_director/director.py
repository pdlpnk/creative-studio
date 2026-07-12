#!/usr/bin/env python3
"""Creative Director agent: local evidence-based planning from Creative Brain."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parents[1]
SEARCH_DIR = PROJECT_ROOT / "brain" / "search"
INSIGHTS_DIR = PROJECT_ROOT / "brain" / "insights"
GENERATOR_DIR = PROJECT_ROOT / "brain" / "generator"
PLANS_DIR = PROJECT_ROOT / "plans"

for directory in [SEARCH_DIR, INSIGHTS_DIR, GENERATOR_DIR]:
    __import__("sys").path.insert(0, str(directory))

from generator import closest_existing, create_plan as generator_recommendations, feature_set, localized_copy, source_ids  # noqa: E402
from index import ConceptCard, load_cards, normalize  # noqa: E402
from insights import build_report  # noqa: E402


@dataclass(frozen=True)
class CreativePlan:
    path: Path
    geo: str
    funnel: str
    count: int
    hypotheses: int


def _context_cards(cards: list[ConceptCard], geo: str, funnel: str) -> list[ConceptCard]:
    return [
        card
        for card in cards
        if normalize(card.value("geo")) == normalize(geo)
        and normalize(card.value("funnel")) == normalize(funnel)
    ]


def _most_common_field(cards: list[ConceptCard], field: str, fallback: str) -> str:
    values = [str(card.value(field)).strip() for card in cards if str(card.value(field) or "").strip()]
    return Counter(values).most_common(1)[0][0] if values else fallback


def _target_compliance(report: dict[str, Any], source_ids_for_plan: list[str]) -> list[str]:
    findings = []
    for finding in report["compliance_analysis"]:
        if finding["id"] in source_ids_for_plan:
            labels = ", ".join(finding["matches"].keys())
            findings.append(f"{finding['id']}: {labels}")
    return findings


def _priority(similarity_score: float, ordinal: int) -> str:
    if similarity_score <= 0.15:
        return "high"
    if similarity_score <= 0.3 or ordinal <= 5:
        return "medium"
    return "low"


def build_plan_markdown(
    *,
    task: str,
    geo: str,
    funnel: str,
    count: int,
    cards: list[ConceptCard],
    report: dict[str, Any],
) -> str:
    """Build a reproducible Creative Plan using only local Brain evidence."""
    scoped_cards = _context_cards(cards, geo, funnel)
    season = _most_common_field(scoped_cards, "season", "not specified in active Brain")
    style = _most_common_field(scoped_cards, "style", "not specified in active Brain")
    generated_plans = generator_recommendations(cards, count, geo=geo, funnel=funnel)
    diversity = report["diversity_analysis"]
    overheated = [
        item["value"]
        for item in report["frequency_analysis"]["compositions"]
        if item["count"] > 1
    ]
    rare_ideas = [item["value"] for item in diversity["rare_colors"][:5]]
    similar_pairs = report["similarity_analysis"]["almost_identical"]
    source_context = [card.id for card in scoped_cards] or [card.id for card in cards[:2]]

    lines = [
        f"# {geo}-{funnel.title()} Creative Plan",
        "",
        "## Goal",
        "",
        task,
        "",
        "## Direction",
        "",
        f"- GEO: {geo}",
        f"- Funnel: {funnel}",
        f"- Planned concepts: {count}",
        f"- Season: {season}",
        f"- Style: {style}",
        f"- Brain references: {', '.join(source_context)}",
        "",
        "## Constraints",
        "",
        "- Do not create images in this planning step.",
        "- Do not use guarantees, refunds, no-loss claims, income promises, fabricated proof or hidden conditions.",
        "- Keep offers factual and make material conditions visible before production.",
        "- These priorities are planning decisions, not performance predictions.",
        "",
        "## What not to repeat",
        "",
    ]
    if overheated:
        lines.extend(f"- Repeated composition pattern: {item}." for item in overheated)
    else:
        lines.append("- No composition exceeded the local repetition threshold; avoid copying any existing card verbatim.")
    for pair in similar_pairs[:3]:
        lines.append(
            f"- Avoid near-duplicating the structural pair {pair['cards'][0]} / {pair['cards'][1]} (similarity {pair['score']})."
        )

    lines.extend(["", "## Overheated and rare ideas", ""])
    lines.append(
        "- Overheated: " + (", ".join(overheated) if overheated else "none above the local threshold") + "."
    )
    lines.append(
        "- Rare visual elements worth controlled exploration: " + (", ".join(rare_ideas) if rare_ideas else "none identified") + "."
    )
    lines.extend(["", "## Hypotheses", ""])

    for ordinal, plan in enumerate(generated_plans, 1):
        copy = localized_copy(plan["geo"], plan["funnel"])
        similarity = closest_existing(
            feature_set(
                plan["colors"],
                plan["objects"],
                copy["offer"],
                copy["cta"],
                plan["composition"],
            ),
            cards,
        )
        sources = source_ids(cards, plan["geo"], plan["funnel"])
        priority = _priority(similarity["score"], ordinal)
        compliance = _target_compliance(report, sources)
        lines.extend(
            [
                f"### H{ordinal:02d} — {plan['idea']}",
                "",
                f"- Priority: {priority}",
                f"- Proposed visual combination: {', '.join(plan['colors'])}; {', '.join(plan['objects'])}; {plan['composition']}.",
                f"- Hypothesis: a safe, information-led {plan['funnel']} message using this currently untested combination may broaden creative diversity without repeating the closest active card.",
                f"- Closest active card: {similarity['id']} ({similarity['score']}).",
                f"- References: {', '.join(sources)}.",
                f"- Why selected: Generator identified the {plan['geo']} / {plan['funnel']} / {plan['colors'][0]} combination as absent from current Insights coverage.",
                f"- Copy direction: {copy['headline']} / {copy['cta']}.",
                "- Compliance direction: no bonus, refund, guarantee, no-loss, income or urgency claim.",
            ]
        )
        if compliance:
            lines.append("- Source review note: " + "; ".join(compliance) + ".")
        lines.append("")

    lines.extend(["## Decision basis", ""])
    lines.append("- All hypotheses are derived from current Brain cards, Insights diversity gaps and Generator candidate plans.")
    lines.append("- No random concept, external research, API call or image generation was used.")
    return "\n".join(lines) + "\n"


def create_and_save_plan(
    geo: str,
    funnel: str,
    count: int = 20,
    task: str | None = None,
    output_dir: Path = PLANS_DIR,
) -> CreativePlan:
    """Create one local decision plan and save it as Markdown."""
    if count < 1:
        raise ValueError("count must be positive")
    cards = load_cards()
    if not cards:
        raise RuntimeError("Creative Brain contains no Concept Cards")
    task = task or f"Create {count} {funnel.title()} {geo} Concept Cards."
    report = build_report(cards)
    content = build_plan_markdown(
        task=task, geo=geo, funnel=funnel, count=count, cards=cards, report=report
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{geo}-{funnel}-plan.md"
    path.write_text(content, encoding="utf-8")
    return CreativePlan(path=path, geo=geo, funnel=funnel, count=count, hypotheses=count)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a local Creative Director plan.")
    parser.add_argument("--geo", choices=("TR", "AZ"), required=True)
    parser.add_argument("--funnel", choices=("registration", "lead"), required=True)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--task")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = create_and_save_plan(args.geo, args.funnel, args.count, args.task)
    print(f"PLAN CREATED: {plan.path.relative_to(PROJECT_ROOT)}")
    print(f"HYPOTHESES: {plan.hypotheses}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
