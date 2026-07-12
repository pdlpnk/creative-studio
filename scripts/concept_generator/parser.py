"""Parse a structured provider response and render a Markdown Concept Card."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping


CONCEPT_ID_PATTERN = re.compile(r"^CC-(\d{4,})$")


def next_concept_id(concepts_dir: Path) -> int:
    """Return the next available numeric Concept ID across all Concept Cards."""
    highest = 0
    for concept_file in concepts_dir.rglob("CC-*.md"):
        match = CONCEPT_ID_PATTERN.match(concept_file.stem)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def parse_model_response(model_response: Mapping[str, Any] | str) -> dict[str, Any]:
    """Accept a provider mapping or JSON object string and validate its top level."""
    if isinstance(model_response, str):
        try:
            parsed = json.loads(model_response)
        except json.JSONDecodeError as error:
            raise ValueError("Model response must be a JSON object or mapping.") from error
    else:
        parsed = dict(model_response)

    required_sections = {
        "general",
        "visual",
        "copy",
        "marketing",
        "design_score",
        "production_notes",
    }
    missing = required_sections.difference(parsed)
    if missing:
        raise ValueError(f"Model response is missing sections: {', '.join(sorted(missing))}")
    return parsed


def _yaml_scalar(value: Any) -> str:
    """Serialize safe front-matter scalars using JSON-compatible YAML syntax."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def _yaml_list(values: Any) -> str:
    if not isinstance(values, list):
        return "[]"
    return json.dumps(values, ensure_ascii=False)


def _section(response: dict[str, Any], name: str) -> dict[str, Any]:
    section = response.get(name, {})
    if not isinstance(section, dict):
        raise ValueError(f"'{name}' must be an object.")
    return section


def render_concept_card(
    model_response: Mapping[str, Any] | str, concept_id: str, image_path: Path
) -> str:
    """Render a validated provider response to a self-contained Markdown card."""
    response = parse_model_response(model_response)
    general = _section(response, "general")
    visual = _section(response, "visual")
    copy = _section(response, "copy")
    marketing = _section(response, "marketing")
    score = _section(response, "design_score")
    notes = _section(response, "production_notes")

    source_path = image_path.as_posix()
    front_matter = [
        "---",
        f"id: {concept_id}",
        f"name: {_yaml_scalar(general.get('filename', image_path.name))}",
        f"asset_url: {_yaml_scalar(source_path)}",
        f"source_hash: {_yaml_scalar(general.get('hash'))}",
        f"source_date: {_yaml_scalar(general.get('date'))}",
        f"geo: {_yaml_scalar(general.get('geo', 'unknown'))}",
        f"funnel: {_yaml_scalar(general.get('funnel', 'unknown'))}",
        f"language: {_yaml_scalar(general.get('language', 'unknown'))}",
        f"creative_type: {_yaml_scalar(general.get('creative_type', ''))}",
        "format: 1080x1080",
        f"headline: {_yaml_scalar(copy.get('headline', ''))}",
        f"supporting_copy: {_yaml_scalar(copy.get('subheadline', ''))}",
        f"cta: {_yaml_scalar(copy.get('cta', ''))}",
        f"offer: {_yaml_scalar(copy.get('offer', ''))}",
        f"hypothesis: {_yaml_scalar('Pending human review of generated analysis.')}",
        f"status: {_yaml_scalar('idea')}",
        f"analysis_status: {_yaml_scalar(response.get('analysis_status', 'pending_review'))}",
        f"primary_colors: {_yaml_list(visual.get('primary_colors'))}",
        f"accent_colors: {_yaml_list(visual.get('accent_colors'))}",
        f"objects: {_yaml_list(visual.get('objects'))}",
        f"emotion: {_yaml_list(visual.get('emotion'))}",
        f"tags: {_yaml_list([])}",
        "---",
    ]

    def field(section: Mapping[str, Any], key: str) -> str:
        value = section.get(key, "")
        if isinstance(value, list):
            return ", ".join(str(item) for item in value) or "—"
        if value is None or value == "":
            return "—"
        return str(value)

    return "\n".join(
        front_matter
        + [
            "",
            "# Summary",
            "",
            f"Source file: `{general.get('filename', image_path.name)}`.",
            "",
            "# General",
            "",
            f"- Hash: `{field(general, 'hash')}`",
            f"- Date: {field(general, 'date')}",
            f"- Geo: {field(general, 'geo')}",
            f"- Funnel: {field(general, 'funnel')}",
            f"- Language: {field(general, 'language')}",
            f"- Creative type: {field(general, 'creative_type')}",
            "",
            "# Visual",
            "",
            f"- Primary colors: {field(visual, 'primary_colors')}",
            f"- Accent colors: {field(visual, 'accent_colors')}",
            f"- Background: {field(visual, 'background')}",
            f"- Composition: {field(visual, 'composition')}",
            f"- Layout: {field(visual, 'layout')}",
            f"- Perspective: {field(visual, 'perspective')}",
            f"- Objects: {field(visual, 'objects')}",
            f"- Phone present: {field(visual, 'phone_present')}",
            f"- Gift present: {field(visual, 'gift_present')}",
            f"- Coins present: {field(visual, 'coins_present')}",
            f"- Person present: {field(visual, 'person_present')}",
            f"- Icons: {field(visual, 'icons')}",
            f"- CTA button: {field(visual, 'cta_button')}",
            f"- Typography: {field(visual, 'typography')}",
            f"- Font weight: {field(visual, 'font_weight')}",
            f"- Contrast: {field(visual, 'contrast')}",
            f"- Spacing: {field(visual, 'spacing')}",
            f"- Visual complexity: {field(visual, 'visual_complexity')}",
            f"- Emotion: {field(visual, 'emotion')}",
            "",
            "# Copy",
            "",
            f"- Headline: {field(copy, 'headline')}",
            f"- Subheadline: {field(copy, 'subheadline')}",
            f"- Offer: {field(copy, 'offer')}",
            f"- CTA: {field(copy, 'cta')}",
            f"- Numbers: {field(copy, 'numbers')}",
            f"- Currency: {field(copy, 'currency')}",
            f"- Language quality: {field(copy, 'language_quality')}",
            f"- Readability: {field(copy, 'readability')}",
            "",
            "# Marketing",
            "",
            f"- Audience: {field(marketing, 'audience')}",
            f"- Pain: {field(marketing, 'pain')}",
            f"- Desire: {field(marketing, 'desire')}",
            f"- Hook: {field(marketing, 'hook')}",
            f"- Trust elements: {field(marketing, 'trust_elements')}",
            f"- Urgency: {field(marketing, 'urgency')}",
            f"- Social proof: {field(marketing, 'social_proof')}",
            f"- Value proposition: {field(marketing, 'value_proposition')}",
            "",
            "# Design Score",
            "",
            f"- Composition: {field(score, 'composition')}",
            f"- Readability: {field(score, 'readability')}",
            f"- Contrast: {field(score, 'contrast')}",
            f"- Hierarchy: {field(score, 'hierarchy')}",
            f"- CTA visibility: {field(score, 'cta_visibility')}",
            f"- Offer visibility: {field(score, 'offer_visibility')}",
            f"- Overall: {field(score, 'overall')}",
            "",
            "# Production Notes",
            "",
            "## Why it may work",
            "",
            field(notes, "why_it_may_work"),
            "",
            "## What is weak",
            "",
            field(notes, "weaknesses"),
            "",
            "## What to test",
            "",
            field(notes, "what_to_test"),
            "",
            "## What to change",
            "",
            field(notes, "what_to_change"),
            "",
            "## What to keep",
            "",
            field(notes, "what_to_keep"),
            "",
        ]
    )


def save_concept_card(
    model_response: Mapping[str, Any] | str,
    concept_id: str,
    image_path: Path,
    concepts_dir: Path,
) -> Path:
    """Write one new Concept Card atomically and refuse to overwrite files."""
    if not CONCEPT_ID_PATTERN.match(concept_id):
        raise ValueError(f"Invalid Concept ID: {concept_id}")

    concepts_dir.mkdir(parents=True, exist_ok=True)
    output_path = concepts_dir / f"{concept_id}.md"
    if output_path.exists():
        raise FileExistsError(f"Concept Card already exists: {output_path}")

    output_path.write_text(
        render_concept_card(model_response, concept_id, image_path), encoding="utf-8"
    )
    return output_path
