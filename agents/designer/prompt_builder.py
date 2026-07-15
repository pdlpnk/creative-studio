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
MARKETING_LIBRARY_DIR = MODULE_DIR / "marketing_library"

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


@dataclass(frozen=True)
class MarketingDecision:
    """The non-visual reason and its resulting visual direction."""

    marketing_hook: str
    emotion: str
    visual_trigger: str
    composition: str
    reason: str


@dataclass(frozen=True)
class RenderedPrompt:
    content: str
    decision: MarketingDecision


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


def _load_library(directory: Path) -> dict[str, dict[str, dict[str, object]]]:
    """Load JSON-compatible YAML without a third-party YAML dependency."""
    result: dict[str, dict[str, dict[str, object]]] = {}
    for path in directory.glob("*.yaml"):
        entries = json.loads(path.read_text(encoding="utf-8"))
        result[path.stem] = {entry["id"]: entry for entry in entries}
    return result


@lru_cache(maxsize=1)
def _visual_library() -> dict[str, dict[str, dict[str, object]]]:
    return _load_library(VISUAL_LIBRARY_DIR)


@lru_cache(maxsize=1)
def _marketing_library() -> dict[str, dict[str, dict[str, object]]]:
    return _load_library(MARKETING_LIBRARY_DIR)


def template_path(geo: str, funnel: str) -> Path:
    path = TEMPLATE_DIR / f"{funnel}_{geo.lower()}.md"
    if not path.is_file():
        raise ValueError(f"No Designer template for {geo}/{funnel}")
    return path


SAFE_MARKETING_ROTATIONS = {
    ("TR", "registration"): ["fast_start", "fast_registration", "easy_start", "notification", "service_discovery"],
    ("AZ", "registration"): ["easy_start", "fast_start", "fast_registration", "notification", "service_discovery"],
    ("TR", "lead"): ["support", "notification", "manager", "easy_start", "service_discovery"],
    ("AZ", "lead"): ["manager", "support", "notification", "easy_start", "service_discovery"],
}
COMPOSITION_BY_PATTERN = {
    "phone_product_shot": ["headline_left_visual_right", "phone_center_cards_around", "visual_center_headline_top"],
    "floating_ui_cards": ["card_stack_with_cta", "phone_center_cards_around", "visual_center_headline_top"],
    "gift_reveal": ["visual_center_headline_top", "headline_left_visual_right"],
    "person_and_phone": ["person_right_offer_left", "headline_left_visual_right"],
    "support_conversation": ["person_right_offer_left", "card_stack_with_cta"],
    "security_and_speed": ["headline_left_visual_right", "phone_center_cards_around"],
}
TRIGGER_OBJECTS = {
    "luxury_phone": ("premium_smartphone", ["simple_ui_cards"]),
    "large_button": ("primary_cta_button", ["simple_ui_cards"]),
    "floating_ui": ("premium_smartphone", ["simple_ui_cards"]),
    "message_notification": ("notification_popup", ["premium_smartphone"]),
    "support_chat": ("support_chat_card", ["adult_woman_with_phone"]),
    "adult_woman_with_smartphone": ("adult_woman_with_phone", ["support_chat_card"]),
    "adult_man_with_smartphone": ("adult_man_with_phone", ["support_chat_card"]),
    "premium_dashboard": ("premium_smartphone", ["simple_ui_cards"]),
}
BACKGROUND_BY_PATTERN = {
    "phone_product_shot": "subtle_grid",
    "floating_ui_cards": "subtle_grid",
    "gift_reveal": "soft_gradient",
    "person_and_phone": "soft_gradient",
    "support_conversation": "soft_gradient",
    "security_and_speed": "clean_surface",
}
STYLE_BY_EMOTION = {
    "simplicity": "minimal mobile-first product direction",
    "confidence": "clean high-contrast product direction",
    "curiosity": "restrained editorial interface direction",
    "trust": "calm human-service direction",
    "discovery": "clear exploratory interface direction",
}
TARGET_COMPOSITION_OFFSET = {
    ("TR", "registration"): 0,
    ("AZ", "registration"): 2,
    ("TR", "lead"): 0,
    ("AZ", "lead"): 1,
}


def _is_confirmed(spec: PromptSpec, hook_id: str) -> bool:
    """Restrict claim-dependent hooks to explicit input text only."""
    source = " ".join([spec.headline, spec.cta, spec.title]).casefold()
    requirements = {
        "cashback": ("cashback",), "usdt": ("usdt",), "crypto": ("crypto", "kripto"),
        "vip": ("vip",), "premium": ("premium",), "exclusive": ("exclusive", "özel"),
        "private_club": ("club", "kulüp"), "live_match": ("match", "maç"),
        "sports_prediction": ("sports", "spor"), "limited_access": ("limited", "sınırlı"),
        "personal_conditions": ("personal", "kişisel"), "verified_account": ("verified", "doğrulan"),
        "success_story": (), "telegram": ("telegram",), "gift": ("gift", "hediye"),
    }
    return hook_id not in requirements or bool(requirements[hook_id]) and any(term in source for term in requirements[hook_id])


def _strategy_candidates(spec: PromptSpec) -> list[tuple[str, str, str, str, str]]:
    marketing = _marketing_library()
    visual = _visual_library()
    groups: list[list[tuple[str, str, str, str, str]]] = []
    for hook_id in SAFE_MARKETING_ROTATIONS[(spec.geo, spec.funnel)]:
        hook = marketing["marketing_hooks"][hook_id]
        works_for = hook["works_best_for"]
        if not works_for[spec.funnel] or spec.geo not in hook["recommended_geos"] or not _is_confirmed(spec, hook_id):
            continue
        group: list[tuple[str, str, str, str, str]] = []
        for trigger_id in hook["recommended_visuals"]:
            if trigger_id not in TRIGGER_OBJECTS:
                continue
            for pattern_id in hook["recommended_patterns"]:
                compositions = COMPOSITION_BY_PATTERN[pattern_id]
                composition_offset = TARGET_COMPOSITION_OFFSET[(spec.geo, spec.funnel)]
                compositions = compositions[composition_offset:] + compositions[:composition_offset]
                for composition_id in compositions:
                    palette_id = hook["recommended_colors"][0]
                    emotion_id = hook["emotion"]
                    if palette_id in visual["palettes"] and emotion_id in marketing["emotions"]:
                        group.append((hook_id, emotion_id, trigger_id, pattern_id, composition_id))
        if group:
            groups.append(group)
    # Interleave hook groups: diversity is visible at the beginning of every batch.
    return [
        candidate
        for position in range(max((len(group) for group in groups), default=0))
        for group in groups
        if position < len(group)
        for candidate in [group[position]]
    ]


def _select_strategy(spec: PromptSpec, used: set[tuple[str, ...]]) -> tuple[str, str, str, str, str]:
    candidates = _strategy_candidates(spec)
    if not candidates:
        raise ValueError("Marketing Library has no compliant strategy for this Creative Plan")
    for offset in range(len(candidates)):
        candidate = candidates[(spec.number - 1 + offset) % len(candidates)]
        hook_id, emotion_id, trigger_id, pattern_id, composition_id = candidate
        palette_id = _marketing_library()["marketing_hooks"][hook_id]["recommended_colors"][0]
        style_id = STYLE_BY_EMOTION.get(emotion_id, "clean mobile-first direction")
        key = (hook_id, emotion_id, trigger_id, composition_id, palette_id, style_id)
        if key not in used:
            used.add(key)
            return candidate
    raise ValueError("Marketing Library has no unused strategy combination for this batch")


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


def build_prompt_with_decision(spec: PromptSpec, used_combinations: set[tuple[str, ...]] | None = None) -> RenderedPrompt:
    """Choose marketing strategy first, then render its compatible visual direction."""
    used = used_combinations if used_combinations is not None else set()
    hook_id, emotion_id, trigger_id, pattern_id, composition_id = _select_strategy(spec, used)
    marketing = _marketing_library()
    library = _visual_library()
    hook = marketing["marketing_hooks"][hook_id]
    pattern = library["patterns"][pattern_id]
    composition = library["compositions"][composition_id]
    primary_id, support_ids = TRIGGER_OBJECTS[trigger_id]
    primary = library["objects"][primary_id]
    supporting = [library["objects"][item]["visual_description"] for item in support_ids[:2]]
    palette_id = hook["recommended_colors"][0]
    palette = library["palettes"][palette_id]
    background = library["backgrounds"][BACKGROUND_BY_PATTERN[pattern_id]]
    emotion = marketing["emotions"][emotion_id]
    template = template_path(spec.geo, spec.funnel).read_text(encoding="utf-8")
    action = "complete registration" if spec.funnel == "registration" else "start a support conversation"
    style = spec.style if not spec.style.startswith("not specified") else "clean mobile-first"
    scene = str(primary["visual_description"])
    if supporting:
        scene += " Supporting element: " + " ".join(str(value) for value in supporting)
    content = template.format(
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
        hook_title=(
            f"Marketing Hook: {hook['title']}\n\n"
            f"Emotion: {emotion_id.title()}\n\n"
            f"Visual Trigger: {trigger_id.replace('_', ' ').title()}"
        ),
        hook_reason=f"Why this works: {hook['psychology']}. Attention score: {hook['attention_score']}/10.",
        scene=scene,
        composition=(
            f"Use {composition_id}: {composition['visual_priority']}. {composition['approximate_canvas_percentages']}. "
            f"Headline area: {composition['headline_area']}; visual area: {composition['visual_area']}; CTA area: {composition['cta_area']}. "
            f"Keep {composition['safe_margins']} and no more than {composition['maximum_text_blocks']} text blocks. Reading flow: {pattern['reading_order']}."
        ),
        visual_style=(
            f"Palette: {palette['description']}. Background: {background['description']}. "
            f"Lighting: soft studio highlight on the hero visual with a grounded shadow; preserve strong text contrast. "
            f"Style: {STYLE_BY_EMOTION.get(emotion_id, style)}. Emotion: {emotion_id.title()}, guided by {emotion['lighting']}."
        ),
        must_avoid=_must_avoid(spec),
    )
    reason = (
        f"{hook['title']} fits {spec.geo} {spec.funnel}; it uses the {emotion_id} emotion and the recommended "
        f"{trigger_id} trigger. {composition_id} follows the {pattern_id} reading pattern."
    )
    return RenderedPrompt(
        content=content,
        decision=MarketingDecision(
            marketing_hook=str(hook["title"]),
            emotion=emotion_id.title(),
            visual_trigger=trigger_id,
            composition=composition_id,
            reason=reason,
        ),
    )


def build_prompt(spec: PromptSpec, used_combinations: set[tuple[str, ...]] | None = None) -> str:
    """Compatibility wrapper used by Designer's existing file writer."""
    return build_prompt_with_decision(spec, used_combinations).content


def prompt_filename(spec: PromptSpec) -> str:
    return f"{spec.geo}-{spec.funnel}-{spec.number:03d}.prompt.md"
