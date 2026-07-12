#!/usr/bin/env python3
"""Local Creative Brain index for Concept Cards.

No network access, AI provider, or third-party YAML package is used. The
parser intentionally supports the simple YAML front matter already present in
``brain/concepts`` and derives additional searchable fields from card bodies.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Sequence


MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parents[1]
DEFAULT_CONCEPTS_DIR = PROJECT_ROOT / "brain" / "concepts"
FRONT_MATTER_PATTERN = re.compile(r"\A---\s*\n(?P<yaml>.*?)\n---\s*\n?(?P<body>.*)\Z", re.DOTALL)
TOP_LEVEL_FIELD = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*):(?:\s*(?P<value>.*))?$")
BULLET_FIELD = re.compile(r"^- (?P<key>[^:]+):\s*(?P<value>.*)$")
NUMBER = re.compile(r"^-?\d+(?:\.\d+)?$")


@dataclass(frozen=True)
class ConceptCard:
    """One indexed Concept Card with normalized derived fields."""

    path: Path
    front_matter: dict[str, Any]
    body: str
    derived: dict[str, Any]

    @property
    def id(self) -> str:
        return str(self.front_matter.get("id", self.path.stem))

    def value(self, key: str, default: Any = "") -> Any:
        return self.front_matter.get(key, default)


def normalize(value: Any) -> str:
    """Return a case-insensitive representation for local matching."""
    return str(value or "").strip().casefold()


def parse_scalar(value: str) -> Any:
    """Parse the limited scalar syntax used by current Concept Card front matter."""
    value = value.strip()
    if value in {"", "null", "~"}:
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    if value.startswith("[") and value.endswith("]"):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return value
        return parsed if isinstance(parsed, list) else value
    if value.startswith('"') and value.endswith('"'):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value[1:-1]
    if NUMBER.match(value):
        return float(value) if "." in value else int(value)
    return value


def parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    """Read simple YAML front matter without depending on a YAML library."""
    match = FRONT_MATTER_PATTERN.match(text)
    if not match:
        return {}, text

    metadata: dict[str, Any] = {}
    active_key: str | None = None
    for line in match.group("yaml").splitlines():
        field = TOP_LEVEL_FIELD.match(line)
        if field:
            active_key = field.group("key")
            metadata[active_key] = parse_scalar(field.group("value") or "")
            continue
        if active_key and line.startswith("  - "):
            if not isinstance(metadata.get(active_key), list):
                metadata[active_key] = []
            metadata[active_key].append(parse_scalar(line[4:]))
            continue
        if line and not line.startswith(" "):
            active_key = None
    return metadata, match.group("body")


def body_bullets(body: str) -> dict[str, str]:
    """Extract top-level ``- Label: value`` fields emitted by parser.py."""
    values: dict[str, str] = {}
    for line in body.splitlines():
        match = BULLET_FIELD.match(line)
        if match:
            values[normalize(match.group("key"))] = match.group("value").strip()
    return values


def markdown_section(body: str, heading: str) -> str:
    """Return one level-one Markdown section without following sections."""
    marker = f"# {heading}\n"
    start = body.find(marker)
    if start < 0:
        return ""
    content_start = start + len(marker)
    next_heading = body.find("\n# ", content_start)
    return body[content_start:] if next_heading < 0 else body[content_start:next_heading]


def split_values(value: Any) -> list[str]:
    """Normalize scalar/list values into meaningful local search values."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text or text in {"—", "none", "null", "unknown"}:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def clean_text(value: Any) -> str:
    """Remove placeholders used by parser-rendered Markdown fields."""
    text = str(value or "").strip()
    return "" if normalize(text) in {"", "—", "none", "null", "unknown"} else text


def numeric_score(value: Any) -> float | None:
    """Return a valid 0–10 score or ``None`` for unavailable card values."""
    try:
        score = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return score if 0 <= score <= 10 else None


def extract_derived_fields(front_matter: dict[str, Any], body: str) -> dict[str, Any]:
    """Unify front matter and Markdown-body fields into searchable attributes."""
    visual_bullets = body_bullets(markdown_section(body, "Visual"))
    copy_bullets = body_bullets(markdown_section(body, "Copy"))
    score_bullets = body_bullets(markdown_section(body, "Design Score"))
    colors = (
        split_values(front_matter.get("colors"))
        + split_values(front_matter.get("primary_colors"))
        + split_values(front_matter.get("accent_colors"))
        + split_values(visual_bullets.get("primary colors"))
        + split_values(visual_bullets.get("accent colors"))
    )
    objects = split_values(front_matter.get("objects")) + split_values(visual_bullets.get("objects"))
    composition = clean_text(front_matter.get("composition") or visual_bullets.get("composition", ""))
    cta = clean_text(front_matter.get("cta") or copy_bullets.get("cta", ""))
    headline = clean_text(front_matter.get("headline") or copy_bullets.get("headline", ""))
    offer = clean_text(front_matter.get("offer") or copy_bullets.get("offer", ""))
    scores = {
        "composition": numeric_score(score_bullets.get("composition")),
        "readability": numeric_score(score_bullets.get("readability")),
        "contrast": numeric_score(score_bullets.get("contrast")),
        "hierarchy": numeric_score(score_bullets.get("hierarchy")),
        "cta_visibility": numeric_score(score_bullets.get("cta visibility")),
        "offer_visibility": numeric_score(score_bullets.get("offer visibility")),
        "overall": numeric_score(score_bullets.get("overall")),
    }
    promise_text = " ".join(
        str(value)
        for value in [offer, headline, front_matter.get("hypothesis", ""), body]
        if value
    )
    return {
        "colors": list(dict.fromkeys(colors)),
        "objects": list(dict.fromkeys(objects)),
        "composition": split_values(composition),
        "cta": cta,
        "headline": headline,
        "offer": offer,
        "promise_text": promise_text,
        "scores": scores,
    }


def load_cards(concepts_dir: Path = DEFAULT_CONCEPTS_DIR) -> list[ConceptCard]:
    """Load every Markdown Concept Card recursively from ``brain/concepts``."""
    if not concepts_dir.is_dir():
        raise FileNotFoundError(f"Concepts directory not found: {concepts_dir}")

    cards: list[ConceptCard] = []
    for path in sorted(concepts_dir.rglob("*.md")):
        if path.name in {"README.md", "template.md"}:
            continue
        front_matter, body = parse_front_matter(path.read_text(encoding="utf-8"))
        cards.append(
            ConceptCard(
                path=path,
                front_matter=front_matter,
                body=body,
                derived=extract_derived_fields(front_matter, body),
            )
        )
    return cards


def _matches_text(value: str, requested: str | None) -> bool:
    return requested is None or normalize(requested) in normalize(value)


def _matches_values(values: Sequence[str], requested: Sequence[str] | None) -> bool:
    if not requested:
        return True
    normalized_values = [normalize(value) for value in values]
    return all(
        any(normalize(query) in value for value in normalized_values)
        for query in requested
    )


def search_cards(
    cards: Iterable[ConceptCard],
    *,
    geo: str | None = None,
    funnel: str | None = None,
    language: str | None = None,
    cta: str | None = None,
    headline: str | None = None,
    objects: Sequence[str] | None = None,
    colors: Sequence[str] | None = None,
    promises: str | None = None,
    min_design_score: float | None = None,
) -> list[ConceptCard]:
    """Return cards matching all supplied local filters."""
    matches: list[ConceptCard] = []
    for card in cards:
        scores = [score for score in card.derived["scores"].values() if score is not None]
        average_score = mean(scores) if scores else None
        if not _matches_text(str(card.value("geo")), geo):
            continue
        if not _matches_text(str(card.value("funnel")), funnel):
            continue
        if not _matches_text(str(card.value("language")), language):
            continue
        if not _matches_text(card.derived["cta"], cta):
            continue
        if not _matches_text(card.derived["headline"], headline):
            continue
        if not _matches_values(card.derived["objects"], objects):
            continue
        if not _matches_values(card.derived["colors"], colors):
            continue
        if not _matches_text(card.derived["promise_text"], promises):
            continue
        if min_design_score is not None and (
            average_score is None or average_score < min_design_score
        ):
            continue
        matches.append(card)
    return matches


def _feature_set(card: ConceptCard) -> set[str]:
    """Build comparable features from visual elements, offer, CTA and composition."""
    features: set[str] = set()
    for color in card.derived["colors"]:
        features.add(f"color:{normalize(color)}")
    for obj in card.derived["objects"]:
        features.add(f"object:{normalize(obj)}")
    for key in ("offer", "cta"):
        value = normalize(card.derived[key])
        if value:
            features.add(f"{key}:{value}")
    for composition in card.derived["composition"]:
        for token in re.findall(r"[\wÀ-ÿ]+", normalize(composition)):
            if len(token) >= 3:
                features.add(f"composition:{token}")
    return features


def similar_creatives(
    cards: Iterable[ConceptCard], target_id: str, limit: int = 3
) -> list[tuple[ConceptCard, float]]:
    """Find local visual/offer/CTA/composition neighbours using Jaccard score."""
    card_list = list(cards)
    target = next((card for card in card_list if card.id == target_id), None)
    if target is None:
        raise ValueError(f"Concept Card not found: {target_id}")
    target_features = _feature_set(target)
    ranked: list[tuple[ConceptCard, float]] = []
    for candidate in card_list:
        if candidate.id == target_id:
            continue
        candidate_features = _feature_set(candidate)
        union = target_features | candidate_features
        score = len(target_features & candidate_features) / len(union) if union else 0.0
        ranked.append((candidate, score))
    return sorted(ranked, key=lambda item: (-item[1], item[0].id))[:limit]


def _top(counter: Counter[str], limit: int = 5) -> list[dict[str, Any]]:
    return [{"value": value, "count": count} for value, count in counter.most_common(limit)]


def library_statistics(cards: Iterable[ConceptCard]) -> dict[str, Any]:
    """Compute local library statistics from indexed Concept Cards."""
    card_list = list(cards)
    geos = Counter(normalize(card.value("geo", "unknown")).upper() or "UNKNOWN" for card in card_list)
    funnels = Counter(normalize(card.value("funnel", "unknown")) or "unknown" for card in card_list)
    ctas = Counter(card.derived["cta"].strip() for card in card_list if card.derived["cta"].strip())
    colors = Counter(color for card in card_list for color in card.derived["colors"])
    objects = Counter(obj for card in card_list for obj in card.derived["objects"])
    overall_scores = [
        card.derived["scores"]["overall"]
        for card in card_list
        if card.derived["scores"]["overall"] is not None
    ]
    all_scores = [
        score
        for card in card_list
        for score in card.derived["scores"].values()
        if score is not None
    ]
    readability_scores = [
        card.derived["scores"]["readability"]
        for card in card_list
        if card.derived["scores"]["readability"] is not None
    ]
    return {
        "card_count": len(card_list),
        "geo": dict(geos),
        "funnel": dict(funnels),
        "popular_cta": _top(ctas),
        "popular_colors": _top(colors),
        "popular_objects": _top(objects),
        "average_design_score": round(mean(overall_scores or all_scores), 2)
        if (overall_scores or all_scores)
        else None,
        "average_readability": round(mean(readability_scores), 2) if readability_scores else None,
    }


def _comma_values(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search local Creative Concept Cards.")
    parser.add_argument("--geo")
    parser.add_argument("--funnel")
    parser.add_argument("--language")
    parser.add_argument("--cta")
    parser.add_argument("--headline")
    parser.add_argument("--objects", help="Comma-separated object terms.")
    parser.add_argument("--colors", help="Comma-separated colour terms.")
    parser.add_argument("--promises")
    parser.add_argument("--min-design-score", type=float)
    parser.add_argument("--similar", metavar="CC_ID", help="Find similar cards for this ID.")
    parser.add_argument("--limit", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cards = load_cards()
    print("Library statistics")
    print(json.dumps(library_statistics(cards), ensure_ascii=False, indent=2))

    has_filters = any(
        value is not None
        for value in [
            args.geo,
            args.funnel,
            args.language,
            args.cta,
            args.headline,
            args.objects,
            args.colors,
            args.promises,
            args.min_design_score,
        ]
    )
    if has_filters:
        results = search_cards(
            cards,
            geo=args.geo,
            funnel=args.funnel,
            language=args.language,
            cta=args.cta,
            headline=args.headline,
            objects=_comma_values(args.objects),
            colors=_comma_values(args.colors),
            promises=args.promises,
            min_design_score=args.min_design_score,
        )
        print("\nSearch results")
        for card in results:
            print(f"- {card.id}: {card.path.relative_to(PROJECT_ROOT)}")
        if not results:
            print("- none")

    target_id = args.similar or (cards[0].id if cards else None)
    if target_id:
        print(f"\nSimilar creatives for {target_id}")
        for card, score in similar_creatives(cards, target_id, args.limit):
            print(f"- {card.id}: {score:.2f} | {card.path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
