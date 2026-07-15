"""Build image-generation prompt files from a Creative Director Markdown plan.

This module is deliberately local: it formats approved plan information only and
does not call an image model or create image assets.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = MODULE_DIR / "templates"
VISUAL_LIBRARY_DIR = MODULE_DIR / "visual_library"

HYPOTHESIS_RE = re.compile(
    r"^### H(?P<number>\d+) — (?P<title>.+?)\n(?P<body>.*?)(?=^### H|^## |\Z)",
    re.MULTILINE | re.DOTALL,
)


@dataclass(frozen=True)
class PromptSpec:
    """One production-ready prompt extracted from a Creative Plan."""

    number: int
    title: str
    geo: str
    funnel: str
    season: str
    style: str
    priority: str
    colors: str
    objects: str
    composition: str
    headline: str
    cta: str
    references: str


def _line_value(text: str, label: str, default: str = "") -> str:
    match = re.search(rf"^- {re.escape(label)}: (?P<value>.+?)$", text, re.MULTILINE)
    return match.group("value").strip().rstrip(".") if match else default


def _direction_value(plan: str, label: str, default: str = "") -> str:
    direction = plan.split("## Direction", 1)
    if len(direction) == 1:
        return default
    return _line_value(direction[1].split("## ", 1)[0], label, default)


def _visual_parts(value: str) -> tuple[str, str, str]:
    """Split the Director's stable `colors; objects; composition` form."""
    parts = [part.strip().rstrip(".") for part in value.split(";", 2)]
    parts.extend(["not specified"] * (3 - len(parts)))
    return parts[0], parts[1], parts[2]


def _copy_parts(value: str) -> tuple[str, str]:
    parts = [part.strip().rstrip(".") for part in value.split(" / ", 1)]
    return (parts[0], parts[1] if len(parts) > 1 else "not specified")


def parse_creative_plan(plan_path: Path) -> list[PromptSpec]:
    """Read a Creative Director plan and return one spec per hypothesis."""
    content = plan_path.read_text(encoding="utf-8")
    geo = _direction_value(content, "GEO")
    funnel = _direction_value(content, "Funnel").lower()
    season = _direction_value(content, "Season", "evergreen")
    style = _direction_value(content, "Style", "minimal")
    if geo not in {"TR", "AZ"} or funnel not in {"registration", "lead"}:
        raise ValueError("Creative Plan must contain supported GEO and Funnel values")

    specs: list[PromptSpec] = []
    for match in HYPOTHESIS_RE.finditer(content):
        body = match.group("body")
        colors, objects, composition = _visual_parts(_line_value(body, "Proposed visual combination"))
        headline, cta = _copy_parts(_line_value(body, "Copy direction"))
        specs.append(
            PromptSpec(
                number=int(match.group("number")),
                title=match.group("title").strip(),
                geo=geo,
                funnel=funnel,
                season=season,
                style=style,
                priority=_line_value(body, "Priority", "medium"),
                colors=colors,
                objects=objects,
                composition=composition,
                headline=headline,
                cta=cta,
                references=_line_value(body, "References", "none"),
            )
        )
    if not specs:
        raise ValueError("Creative Plan contains no hypotheses to design")
    return specs


@lru_cache(maxsize=1)
def _library() -> dict[str, dict[str, dict[str, object]]]:
    """Load JSON-compatible YAML without a third-party YAML dependency."""
    result: dict[str, dict[str, dict[str, object]]] = {}
    for path in VISUAL_LIBRARY_DIR.glob("*.yaml"):
        entries = json.loads(path.read_text(encoding="utf-8"))
        result[path.stem] = {entry["id"]: entry for entry in entries}
    return result


def template_path(geo: str, funnel: str) -> Path:
    path = TEMPLATE_DIR / f"{funnel}_{geo.lower()}.md"
    if not path.is_file():
        raise ValueError(f"No Designer template for {geo}/{funnel}")
    return path


SAFE_HOOK_ROTATIONS = {
    ("TR", "registration"): ["phone_interface", "gift_box", "notification_card", "security_shield", "adult_person_with_phone"],
    ("AZ", "registration"): ["gift_box", "notification_card", "phone_interface", "security_shield", "adult_person_with_phone"],
    ("TR", "lead"): ["support_manager", "phone_interface", "notification_card", "security_shield", "adult_person_with_phone"],
    ("AZ", "lead"): ["notification_card", "support_manager", "phone_interface", "security_shield", "adult_person_with_phone"],
}
PATTERN_BY_HOOK = {
    "phone_interface": ["phone_product_shot", "floating_ui_cards"],
    "gift_box": ["gift_reveal", "person_and_phone"],
    "notification_card": ["floating_ui_cards", "phone_product_shot"],
    "support_manager": ["support_conversation", "person_and_phone"],
    "security_shield": ["security_and_speed", "phone_product_shot"],
    "adult_person_with_phone": ["person_and_phone", "phone_product_shot"],
}
COMPOSITION_BY_PATTERN = {
    "phone_product_shot": ["headline_left_visual_right", "phone_center_cards_around"],
    "floating_ui_cards": ["card_stack_with_cta", "phone_center_cards_around"],
    "gift_reveal": ["visual_center_headline_top", "headline_left_visual_right"],
    "person_and_phone": ["person_right_offer_left", "headline_left_visual_right"],
    "support_conversation": ["person_right_offer_left", "card_stack_with_cta"],
    "security_and_speed": ["headline_left_visual_right", "phone_center_cards_around"],
}
PRIMARY_OBJECT_BY_HOOK = {
    "phone_interface": "premium_smartphone",
    "gift_box": "gift_box",
    "notification_card": "notification_popup",
    "support_manager": "adult_man_with_phone",
    "security_shield": "shield",
    "adult_person_with_phone": "adult_woman_with_phone",
}
SUPPORT_OBJECTS_BY_HOOK = {
    "phone_interface": ["simple_ui_cards", "notification_popup"],
    "gift_box": ["premium_smartphone"],
    "notification_card": ["premium_smartphone"],
    "support_manager": ["support_chat_card"],
    "security_shield": ["premium_smartphone"],
    "adult_person_with_phone": ["support_chat_card"],
}
PALETTE_BY_HOOK = {
    "phone_interface": "clear_blue",
    "gift_box": "warm_welcome",
    "notification_card": "clean_neutral",
    "support_manager": "clear_blue",
    "security_shield": "clean_neutral",
    "adult_person_with_phone": "clear_blue",
}
BACKGROUND_BY_PATTERN = {
    "phone_product_shot": "subtle_grid",
    "floating_ui_cards": "subtle_grid",
    "gift_reveal": "soft_gradient",
    "person_and_phone": "soft_gradient",
    "support_conversation": "soft_gradient",
    "security_and_speed": "clean_surface",
}
EMOTION_BY_HOOK = {
    "phone_interface": "confidence",
    "gift_box": "excitement",
    "notification_card": "curiosity",
    "support_manager": "trust",
    "security_shield": "reassurance",
    "adult_person_with_phone": "trust",
}


def _choice(values: list[str], index: int) -> str:
    return values[index % len(values)]


def _selection(spec: PromptSpec, used: set[tuple[str, str, str]]) -> tuple[str, str, str]:
    hooks = SAFE_HOOK_ROTATIONS[(spec.geo, spec.funnel)]
    candidates = [
        (hook, pattern, composition)
        for hook in hooks
        for pattern in PATTERN_BY_HOOK[hook]
        for composition in COMPOSITION_BY_PATTERN[pattern]
    ]
    for offset in range(len(candidates)):
        key = candidates[(spec.number - 1 + offset) % len(candidates)]
        if key not in used:
            used.add(key)
            return key
    raise ValueError("Visual Library has no unused hook/pattern/composition combination")


def _approved_supporting_copy() -> str:
    return "Not provided in the Creative Plan; do not add supporting copy."


def _must_avoid(spec: PromptSpec) -> str:
    seasonal = "- No snow, winter styling or Christmas cues.\n" if spec.season.lower() == "summer" else ""
    return (
        seasonal
        + "- No additional offer text, amounts, bonuses, cashback, deadline, testimonial, payout, statistic or result claim.\n"
        "- No minors, teen styling, real celebrities, protected brands, cash piles, gambling-as-work imagery or financial-dashboard UI.\n"
        "- No guarantee, income, refund, no-loss or risk-free wording; no hidden material conditions.\n"
        "- No tiny text, busy collage, unreadable pseudo-text, extra icons, watermark or cropped CTA."
    )


def build_prompt(spec: PromptSpec, used_combinations: set[tuple[str, str, str]] | None = None) -> str:
    """Create one concise, compliance-aware advertising prompt from local visual rules."""
    used = used_combinations if used_combinations is not None else set()
    hook_id, pattern_id, composition_id = _selection(spec, used)
    library = _library()
    hook = library["hooks"][hook_id]
    pattern = library["patterns"][pattern_id]
    composition = library["compositions"][composition_id]
    primary = library["objects"][PRIMARY_OBJECT_BY_HOOK[hook_id]]
    support_ids = SUPPORT_OBJECTS_BY_HOOK[hook_id][:2]
    supporting = [library["objects"][item]["visual_description"] for item in support_ids]
    palette = library["palettes"][PALETTE_BY_HOOK[hook_id]]
    background = library["backgrounds"][BACKGROUND_BY_PATTERN[pattern_id]]
    emotion = library["emotions"][EMOTION_BY_HOOK[hook_id]]
    template = template_path(spec.geo, spec.funnel).read_text(encoding="utf-8")
    action = "complete registration" if spec.funnel == "registration" else "start a support conversation"
    style = spec.style if not spec.style.startswith("not specified") else "clean mobile-first"
    scene = str(primary["visual_description"])
    if supporting:
        scene += " Supporting element: " + " ".join(str(value) for value in supporting)
    return template.format(
        number=f"{spec.number:03d}",
        geo=spec.geo,
        funnel=spec.funnel.title(),
        language=spec.geo,
        creative_intent=(
            f"Make the approved CTA feel like one clear next step: {action}. In the first second, communicate a simple service action without promising a result, reward or financial outcome."
        ),
        approved_headline=spec.headline,
        approved_supporting_copy=_approved_supporting_copy(),
        approved_cta=spec.cta,
        hook_title=hook["title"],
        hook_reason=hook["purpose"],
        scene=scene,
        composition=(
            f"Use {composition_id}: {composition['visual_priority']}. {composition['approximate_canvas_percentages']}. "
            f"Headline area: {composition['headline_area']}; visual area: {composition['visual_area']}; CTA area: {composition['cta_area']}. "
            f"Keep {composition['safe_margins']} and no more than {composition['maximum_text_blocks']} text blocks. Reading flow: {pattern['reading_order']}."
        ),
        visual_style=(
            f"Palette: {palette['description']}. Background: {background['description']}. "
            f"Lighting: soft studio highlight on the hero visual with a grounded shadow; preserve strong text contrast. "
            f"Style: clean, contemporary {style} advertising art direction. Emotion: {emotion['description']}"
        ),
        must_avoid=_must_avoid(spec),
    )


def prompt_filename(spec: PromptSpec) -> str:
    return f"{spec.geo}-{spec.funnel}-{spec.number:03d}.prompt.md"
