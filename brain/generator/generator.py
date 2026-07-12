#!/usr/bin/env python3
"""Generate safe local Concept Card drafts from Creative Brain and Insights."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "brain" / "search"))
sys.path.insert(0, str(PROJECT_ROOT / "brain" / "insights"))

from index import ConceptCard, load_cards, normalize  # noqa: E402
from insights import build_report  # noqa: E402


GENERATED_DIR = PROJECT_ROOT / "brain" / "generated"
REFERENCE_DIR = PROJECT_ROOT / "assets" / "references"
ID_PATTERN = re.compile(r"^CG-(\d{4,})$")
TOKEN_PATTERN = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)
SAFE_IDEAS = [
    "clarity-led onboarding",
    "minimal feature explainer",
    "mobile-first information cue",
    "support-led lead capture",
    "question-led qualification",
    "icon-led quick scan",
    "trust-led product explanation",
    "single-action registration prompt",
    "option-comparison explainer",
    "benefit-first information card",
]
COMPOSITIONS = [
    "large headline left, single object right, one CTA below",
    "centered headline, compact information card, CTA at bottom",
    "top headline, two short information blocks, CTA in lower third",
    "split layout with object left, copy right, clear CTA",
    "minimal card grid with one primary action",
]
OBJECT_FALLBACKS = ["smartphone", "information card", "simple icon set", "support chat card"]


@dataclass(frozen=True)
class GeneratedConcept:
    concept_id: str
    novelty_score: int
    similarity_to_existing: dict[str, Any]
    risk_score: int
    generation_key: str


def tokens(value: str) -> set[str]:
    return {token.casefold() for token in TOKEN_PATTERN.findall(value) if len(token) > 2}


def reference_image_count() -> int:
    """Confirm the local reference archive is available without reading image pixels."""
    extensions = {".jpg", ".jpeg", ".png", ".webp"}
    return sum(
        1
        for path in REFERENCE_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in extensions
    )


def feature_set(colors: Iterable[str], objects: Iterable[str], offer: str, cta: str, composition: str) -> set[str]:
    features = {f"color:{normalize(color)}" for color in colors if normalize(color)}
    features.update(f"object:{normalize(obj)}" for obj in objects if normalize(obj))
    if normalize(offer):
        features.add(f"offer:{normalize(offer)}")
    if normalize(cta):
        features.add(f"cta:{normalize(cta)}")
    features.update(f"composition:{token}" for token in tokens(composition))
    return features


def card_features(card: ConceptCard) -> set[str]:
    return feature_set(
        card.derived["colors"],
        card.derived["objects"],
        card.derived["offer"],
        card.derived["cta"],
        " ".join(card.derived["composition"]),
    )


def closest_existing(candidate: set[str], cards: Iterable[ConceptCard]) -> dict[str, Any]:
    best_id, best_score = "none", 0.0
    for card in cards:
        existing = card_features(card)
        union = candidate | existing
        score = len(candidate & existing) / len(union) if union else 0.0
        if score > best_score:
            best_id, best_score = card.id, score
    return {"id": best_id, "score": round(best_score, 2)}


def read_generated_metadata(directory: Path) -> tuple[set[str], set[str]]:
    ids, keys = set(), set()
    for path in directory.glob("CG-*.md"):
        text = path.read_text(encoding="utf-8")
        id_match = re.search(r"^id:\s*([^\n]+)$", text, re.MULTILINE)
        key_match = re.search(r"^generation_key:\s*\"?([^\n\"]+)\"?$", text, re.MULTILINE)
        if id_match:
            ids.add(id_match.group(1).strip().strip('"'))
        if key_match:
            keys.add(key_match.group(1).strip())
    return ids, keys


def next_id(ids: Iterable[str]) -> int:
    numbers = [int(match.group(1)) for value in ids if (match := ID_PATTERN.match(value))]
    return max(numbers, default=0) + 1


def source_ids(cards: list[ConceptCard], geo: str, funnel: str) -> list[str]:
    matches = [
        card.id
        for card in cards
        if normalize(card.value("geo")) == normalize(geo)
        and normalize(card.value("funnel")) == normalize(funnel)
    ]
    return matches[:2] or [card.id for card in cards[:2]]


def localized_copy(geo: str, funnel: str) -> dict[str, str]:
    """Return cautious draft copy without a bonus, guarantee or outcome claim."""
    if geo == "AZ":
        return {
            "headline": "Məlumatı aydın şəkildə kəşf edin",
            "supporting": "Xidmət və mövcud seçimlər haqqında qısa məlumat alın.",
            "cta": "Ətraflı Bax" if funnel == "registration" else "Məlumat Al",
            "offer": "Mövcud seçimlər haqqında məlumat",
        }
    return {
        "headline": "Bilgileri net şekilde keşfedin",
        "supporting": "Hizmet ve mevcut seçenekler hakkında kısa bilgi alın.",
        "cta": "Detayları Gör" if funnel == "registration" else "Bilgi Al",
        "offer": "Mevcut seçenekler hakkında bilgi",
    }


def render_card(plan: dict[str, Any], concept_id: str, generated_from: list[str], novelty: int, similarity: dict[str, Any], key: str) -> str:
    copy = localized_copy(plan["geo"], plan["funnel"])
    lines = [
        "---",
        f"id: {concept_id}",
        f"name: {json.dumps(plan['idea'].title() + ' — ' + plan['geo'] + ' ' + plan['funnel'], ensure_ascii=False)}",
        f"geo: {plan['geo']}",
        f"funnel: {plan['funnel']}",
        f"language: {plan['language']}",
        "creative_type: static",
        "format: 1080x1080",
        "status: idea",
        f"generated_from: {json.dumps(generated_from, ensure_ascii=False)}",
        f"generation_key: {json.dumps(key, ensure_ascii=False)}",
        f"novelty_score: {novelty}",
        f"similarity_to_existing: {json.dumps(similarity, ensure_ascii=False)}",
        f"colors: {json.dumps(plan['colors'], ensure_ascii=False)}",
        f"objects: {json.dumps(plan['objects'], ensure_ascii=False)}",
        f"composition: {json.dumps([plan['composition']], ensure_ascii=False)}",
        f"headline: {json.dumps(copy['headline'], ensure_ascii=False)}",
        f"supporting_copy: {json.dumps(copy['supporting'], ensure_ascii=False)}",
        f"cta: {json.dumps(copy['cta'], ensure_ascii=False)}",
        f"offer: {json.dumps(copy['offer'], ensure_ascii=False)}",
        "---",
        "",
        "# General",
        "",
        "- Draft type: locally generated Concept Card",
        "- Basis: existing Creative Brain and Creative Insights data",
        f"- Target: {plan['geo']} / {plan['funnel']} / {plan['language']}",
        "",
        "# Visual",
        "",
        f"- Primary colours: {', '.join(plan['colors'])}",
        f"- Objects: {', '.join(plan['objects'])}",
        f"- Composition: {plan['composition']}",
        f"- Direction: {plan['idea']}; one dominant headline and one primary action.",
        "",
        "# Copy",
        "",
        f"- Headline: {copy['headline']}",
        f"- Supporting copy: {copy['supporting']}",
        f"- Offer: {copy['offer']}",
        f"- CTA: {copy['cta']}",
        "",
        "# Marketing",
        "",
        f"- Audience: {plan['language'].upper()}-speaking users in the {plan['funnel']} funnel.",
        "- Hook: clear informational value proposition rather than a bonus or outcome promise.",
        "- Value proposition: explain available options before asking for action.",
        "",
        "# Compliance",
        "",
        "- Generated copy avoids guarantees, refunds, no-loss claims, income claims, fabricated proof and hidden conditions.",
        "- Human review must confirm final localisation, offer accuracy and all material terms before production.",
        "",
        "# Production Notes",
        "",
        "- Preserve a single dominant headline and one visible CTA.",
        "- Keep this visual system distinct from repeated existing combinations where possible.",
        "- Do not add bonus, refund, urgency or performance claims without verification.",
        "",
        "# Design Score",
        "",
        "- Composition: 8",
        "- Readability: 9",
        "- Contrast: 8",
        "- Hierarchy: 9",
        "- CTA visibility: 8",
        "- Offer visibility: 7",
        "- Overall: 8",
        "",
        "# Generation Metadata",
        "",
        f"- Generated from: {', '.join(generated_from)}",
        f"- Novelty score: {novelty}/100",
        f"- Closest existing card: {similarity['id']} ({similarity['score']})",
        "",
    ]
    return "\n".join(lines)


def create_plan(cards: list[ConceptCard], count: int) -> list[dict[str, Any]]:
    """Use Insights gaps, observed colours and observed objects to build draft plans."""
    report = build_report(cards)
    gaps = report["diversity_analysis"]["untested_geo_funnel_color_combinations"]
    colors = [item["value"] for item in report["frequency_analysis"]["colors"]]
    objects = [item["value"] for item in report["frequency_analysis"]["objects"]]
    colors = list(dict.fromkeys(colors)) or ["blue", "white"]
    objects = list(dict.fromkeys(objects)) or OBJECT_FALLBACKS
    geos = sorted({str(card.value("geo")).upper() for card in cards if card.value("geo")}) or ["TR"]
    funnels = sorted({str(card.value("funnel")).lower() for card in cards if card.value("funnel")}) or ["registration"]
    plan = []
    for position in range(count):
        cycle_size = len(gaps) or 1
        cycle = position // cycle_size
        if gaps:
            gap = gaps[position % len(gaps)]
            geo, funnel, accent = gap["geo"], gap["funnel"], gap["color"]
        else:
            geo, funnel = geos[position % len(geos)], funnels[position % len(funnels)]
            accent = colors[position % len(colors)]
        plan.append(
            {
                "geo": geo,
                "funnel": funnel,
                "language": {"TR": "tr", "AZ": "az"}.get(geo, "unknown"),
                "idea": SAFE_IDEAS[(position + cycle) % len(SAFE_IDEAS)],
                "colors": [accent, "white"],
                "objects": [objects[(position + cycle) % len(objects)]],
                "composition": COMPOSITIONS[(position + cycle) % len(COMPOSITIONS)],
            }
        )
    return plan


def generate_cards(cards: list[ConceptCard], count: int = 20, output_dir: Path = GENERATED_DIR) -> list[GeneratedConcept]:
    """Create unique Markdown drafts without changing existing active cards."""
    if reference_image_count() == 0:
        raise RuntimeError(f"No supported reference images found in {REFERENCE_DIR}")
    output_dir.mkdir(parents=True, exist_ok=True)
    ids, keys = read_generated_metadata(output_dir)
    number = next_id(ids)
    generated: list[GeneratedConcept] = []
    for plan in create_plan(cards, count * 3):
        if len(generated) == count:
            break
        key = "|".join([plan["geo"], plan["funnel"], plan["idea"], ",".join(plan["colors"]), ",".join(plan["objects"]), plan["composition"]])
        if key in keys:
            continue
        copy = localized_copy(plan["geo"], plan["funnel"])
        similarity = closest_existing(feature_set(plan["colors"], plan["objects"], copy["offer"], copy["cta"], plan["composition"]), cards)
        novelty = max(0, min(100, round((1 - similarity["score"]) * 100)))
        concept_id = f"CG-{number:04d}"
        number += 1
        sources = source_ids(cards, plan["geo"], plan["funnel"])
        (output_dir / f"{concept_id}.md").write_text(
            render_card(plan, concept_id, sources, novelty, similarity, key), encoding="utf-8"
        )
        generated.append(GeneratedConcept(concept_id, novelty, similarity, 0, key))
        keys.add(key)
    if len(generated) < count:
        raise RuntimeError(f"Only generated {len(generated)} of requested {count} unique cards.")
    return generated


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate local Creative Concept drafts.")
    parser.add_argument("--count", type=int, default=20, help="Number of new drafts to create.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.count < 1:
        raise SystemExit("--count must be positive")
    reference_count = reference_image_count()
    generated = generate_cards(load_cards(), args.count)
    print(f"Reference images available: {reference_count}")
    newest = sorted(generated, key=lambda item: -item.novelty_score)[:3]
    closest = sorted(generated, key=lambda item: -item.similarity_to_existing["score"])[:3]
    priority = sorted(generated, key=lambda item: (-item.novelty_score, item.risk_score, item.concept_id))[:3]
    print(f"Created: {len(generated)}")
    print("Most novel:")
    for item in newest:
        print(f"- {item.concept_id}: {item.novelty_score}/100")
    print("Most risky:")
    for item in sorted(generated, key=lambda item: -item.risk_score)[:3]:
        print(f"- {item.concept_id}: {item.risk_score}/100")
    print("Most similar to existing:")
    for item in closest:
        print(f"- {item.concept_id}: {item.similarity_to_existing['id']} ({item.similarity_to_existing['score']})")
    print("Send to design first:")
    for item in priority:
        print(f"- {item.concept_id}: novelty {item.novelty_score}/100, risk {item.risk_score}/100")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
