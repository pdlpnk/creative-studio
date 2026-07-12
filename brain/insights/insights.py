#!/usr/bin/env python3
"""Local, evidence-based insights over Creative Brain Concept Cards."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path
from statistics import mean
from typing import Any, Iterable


MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parents[1]
SEARCH_DIR = PROJECT_ROOT / "brain" / "search"
sys.path.insert(0, str(SEARCH_DIR))

from index import ConceptCard, library_statistics, load_cards, normalize, similar_creatives  # noqa: E402


WORD_PATTERN = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)
BONUS_PATTERN = re.compile(
    r"\b(?:promo|free\s*bet|free|bonus|\d+\s*(?:tl|azn))\b", re.IGNORECASE
)
COMPLIANCE_PATTERNS = {
    "guarantee": re.compile(r"\b(?:guarantee|garanti|guaranteed)\b", re.IGNORECASE),
    "refund": re.compile(
        r"(?:geri\s+ver|geri\s+qay|iade|refund|return|mevduat.*geri)", re.IGNORECASE
    ),
    "no_risk": re.compile(
        r"(?:kaybetm|itirm|no\s+loss|risk.?free|heç\s+bir\s+halda)", re.IGNORECASE
    ),
    "verification_words": re.compile(
        r"\b(?:free|promo|bonus|kazan|kazanç|hemen|limited|sınırlı|məhdud|acele|tələs)\b",
        re.IGNORECASE,
    ),
}


def text_tokens(text: str) -> set[str]:
    """Create a small language-agnostic token set for local lexical comparison."""
    return {token.casefold() for token in WORD_PATTERN.findall(text) if len(token) > 2}


def card_copy_text(card: ConceptCard) -> str:
    """Use only fields already indexed by Creative Brain."""
    return " ".join(
        [
            card.derived["headline"],
            card.derived["offer"],
            card.derived["cta"],
            str(card.value("supporting_copy", "")),
        ]
    )


def top(counter: Counter[str], limit: int = 5) -> list[dict[str, Any]]:
    return [{"value": key, "count": count} for key, count in counter.most_common(limit)]


def headline_patterns(cards: Iterable[ConceptCard], limit: int = 8) -> list[dict[str, Any]]:
    """Return frequent non-trivial headline tokens as observed patterns."""
    ignored = {"bir", "ve", "ile", "the", "for", "free"}
    counts = Counter(
        token
        for card in cards
        for token in text_tokens(card.derived["headline"])
        if token not in ignored and not token.isdigit()
    )
    return top(counts, limit)


def bonus_phrases(cards: Iterable[ConceptCard], limit: int = 8) -> list[dict[str, Any]]:
    """Extract promotion-like phrases actually visible in card copy."""
    counts: Counter[str] = Counter()
    for card in cards:
        for match in BONUS_PATTERN.finditer(card_copy_text(card)):
            counts[match.group(0).upper()] += 1
    return top(counts, limit)


def frequency_analysis(cards: Iterable[ConceptCard]) -> dict[str, Any]:
    """Compute observed TOP CTA, headline, visual, bonus, promise and composition data."""
    card_list = list(cards)
    ctas = Counter(card.derived["cta"] for card in card_list if card.derived["cta"])
    colors = Counter(color for card in card_list for color in card.derived["colors"])
    objects = Counter(obj for card in card_list for obj in card.derived["objects"])
    compositions = Counter(
        "; ".join(card.derived["composition"])
        for card in card_list
        if card.derived["composition"]
    )
    promises = Counter(
        card.derived["offer"]
        for card in card_list
        if card.derived["offer"]
    )
    return {
        "cta": top(ctas),
        "headline_patterns": headline_patterns(card_list),
        "colors": top(colors),
        "objects": top(objects),
        "bonuses": bonus_phrases(card_list),
        "promises": top(promises),
        "compositions": top(compositions),
    }


def general_analytics(cards: Iterable[ConceptCard]) -> dict[str, Any]:
    """Extend Creative Brain's statistics with the required language split."""
    card_list = list(cards)
    report = library_statistics(card_list)
    report["language"] = dict(
        Counter(normalize(card.value("language", "unknown")) or "unknown" for card in card_list)
    )
    return report


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def similarity_analysis(cards: Iterable[ConceptCard], threshold: float = 0.35) -> dict[str, Any]:
    """Find structural and lexical neighbours without semantic-model inference."""
    card_list = list(cards)
    structural_pairs: list[dict[str, Any]] = []
    semantic_pairs: list[dict[str, Any]] = []
    offer_pairs: list[dict[str, Any]] = []
    cta_pairs: list[dict[str, Any]] = []

    structural_by_pair: dict[tuple[str, str], float] = {}
    for card in card_list:
        for candidate, score in similar_creatives(card_list, card.id, limit=len(card_list)):
            pair = tuple(sorted((card.id, candidate.id)))
            structural_by_pair[pair] = max(structural_by_pair.get(pair, 0.0), score)

    for left, right in combinations(card_list, 2):
        structural = structural_by_pair.get(tuple(sorted((left.id, right.id))), 0.0)
        if structural >= threshold:
            structural_pairs.append({"cards": [left.id, right.id], "score": round(structural, 2)})

        copy_score = jaccard(text_tokens(card_copy_text(left)), text_tokens(card_copy_text(right)))
        if copy_score >= threshold:
            semantic_pairs.append({"cards": [left.id, right.id], "score": round(copy_score, 2)})

        offer_score = jaccard(
            text_tokens(left.derived["offer"]), text_tokens(right.derived["offer"])
        )
        if offer_score >= threshold:
            offer_pairs.append({"cards": [left.id, right.id], "score": round(offer_score, 2)})

        left_cta = normalize(left.derived["cta"])
        right_cta = normalize(right.derived["cta"])
        if left_cta and right_cta and left_cta == right_cta:
            cta_pairs.append({"cards": [left.id, right.id], "score": 1.0})

    sort_pairs = lambda pairs: sorted(pairs, key=lambda pair: (-pair["score"], pair["cards"]))
    return {
        "almost_identical": sort_pairs(structural_pairs),
        "lexically_similar_copy": sort_pairs(semantic_pairs),
        "similar_offers": sort_pairs(offer_pairs),
        "similar_cta": sort_pairs(cta_pairs),
    }


def diversity_analysis(cards: Iterable[ConceptCard]) -> dict[str, Any]:
    """Identify concentration and unobserved combinations in current card metadata."""
    card_list = list(cards)
    idea_counts = Counter(
        normalize(card.derived["headline"] or card.derived["offer"])
        for card in card_list
        if card.derived["headline"] or card.derived["offer"]
    )
    color_counts = Counter(color for card in card_list for color in card.derived["colors"])
    object_counts = Counter(obj for card in card_list for obj in card.derived["objects"])
    present_geo_funnel_color = {
        (normalize(card.value("geo")), normalize(card.value("funnel")), normalize(color))
        for card in card_list
        for color in card.derived["colors"]
    }
    geos = sorted({normalize(card.value("geo")) for card in card_list if card.value("geo")})
    funnels = sorted({normalize(card.value("funnel")) for card in card_list if card.value("funnel")})
    candidate_colors = [color for color, _ in color_counts.most_common(5)]
    untested = [
        {"geo": geo.upper(), "funnel": funnel, "color": color}
        for geo in geos
        for funnel in funnels
        for color in candidate_colors
        if (geo, funnel, normalize(color)) not in present_geo_funnel_color
    ]
    return {
        "overused_ideas": top(Counter({key: count for key, count in idea_counts.items() if count > 1})),
        "rare_colors": top(Counter({key: count for key, count in color_counts.items() if count == 1})),
        "rare_objects": top(Counter({key: count for key, count in object_counts.items() if count == 1})),
        "untested_geo_funnel_color_combinations": untested[:10],
    }


def compliance_analysis(cards: Iterable[ConceptCard]) -> list[dict[str, Any]]:
    """Flag visible card text that needs human verification or compliance review."""
    findings: list[dict[str, Any]] = []
    for card in cards:
        text = card_copy_text(card)
        matches = {
            category: pattern.findall(text)
            for category, pattern in COMPLIANCE_PATTERNS.items()
        }
        filtered = {key: value for key, value in matches.items() if value}
        if filtered:
            findings.append({"id": card.id, "matches": filtered})
    return findings


def opportunity_report(cards: Iterable[ConceptCard]) -> list[str]:
    """Create data-dependent recommendations from observed local gaps only."""
    card_list = list(cards)
    opportunities: list[str] = []
    color_counts = Counter(color for card in card_list for color in card.derived["colors"])
    if color_counts:
        rare = [color for color, count in color_counts.items() if count == 1]
        if rare:
            opportunities.append(
                "Rare visual elements to test: " + ", ".join(sorted(rare)[:3]) + "."
            )

    no_numbers = [card.id for card in card_list if not re.search(r"\d", card_copy_text(card))]
    if no_numbers:
        opportunities.append(
            f"{len(no_numbers)} of {len(card_list)} cards use no visible number in headline/offer/CTA; "
            "a number-led versus number-free comparison is available."
        )

    no_bonus = [card.id for card in card_list if not BONUS_PATTERN.search(card_copy_text(card))]
    if no_bonus:
        opportunities.append(
            f"{len(no_bonus)} of {len(card_list)} cards have no observed bonus phrase; "
            "compare a non-bonus value proposition with bonus-led copy."
        )

    words_per_card = {
        card.id: len(text_tokens(card_copy_text(card))) for card in card_list
    }
    minimal = [card_id for card_id, count in words_per_card.items() if count <= 5]
    if not minimal:
        opportunities.append(
            "No card has five or fewer meaningful copy tokens; test a minimal-text variant."
        )

    diversity = diversity_analysis(card_list)
    missing = diversity["untested_geo_funnel_color_combinations"]
    if missing:
        sample = missing[0]
        opportunities.append(
            "Untested observed-color combination: "
            f"{sample['geo']} / {sample['funnel']} / {sample['color']}."
        )
    return opportunities


def build_report(cards: Iterable[ConceptCard]) -> dict[str, Any]:
    """Return every Creative Insights v1 section as one serializable report."""
    card_list = list(cards)
    return {
        "general_analytics": general_analytics(card_list),
        "frequency_analysis": frequency_analysis(card_list),
        "similarity_analysis": similarity_analysis(card_list),
        "diversity_analysis": diversity_analysis(card_list),
        "compliance_analysis": compliance_analysis(card_list),
        "opportunity_report": opportunity_report(card_list),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate local Creative Insights.")
    parser.add_argument("--json", action="store_true", help="Print the full report as JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cards = load_cards()
    report = build_report(cards)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    general = report["general_analytics"]
    print("Creative Insights v1")
    print(f"Cards: {general['card_count']}")
    print(f"GEO: {general['geo']}")
    print(f"Funnel: {general['funnel']}")
    print(f"Language: {general['language']}")
    print(f"Average design score: {general['average_design_score']}")
    print(f"Average readability: {general['average_readability']}")

    print("\nRecommendations")
    for item in report["opportunity_report"]:
        print(f"- {item}")

    print("\nSimilar cards")
    pairs = report["similarity_analysis"]["almost_identical"]
    if pairs:
        for pair in pairs:
            print(f"- {pair['cards'][0]} / {pair['cards'][1]}: {pair['score']}")
    else:
        print("- No high structural-similarity pairs found.")

    print("\nPossible directions for new tests")
    for item in report["diversity_analysis"]["untested_geo_funnel_color_combinations"][:3]:
        print(f"- {item['geo']} / {item['funnel']} / {item['color']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
