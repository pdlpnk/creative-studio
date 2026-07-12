"""Build image-generation prompt files from a Creative Director Markdown plan.

This module is deliberately local: it formats approved plan information only and
does not call an image model or create image assets.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = MODULE_DIR / "templates"

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


def template_path(geo: str, funnel: str) -> Path:
    path = TEMPLATE_DIR / f"{funnel}_{geo.lower()}.md"
    if not path.is_file():
        raise ValueError(f"No Designer template for {geo}/{funnel}")
    return path


def _emotion(spec: PromptSpec) -> str:
    title = spec.title.lower()
    if any(word in title for word in ("trust", "support")):
        return "Trust"
    if any(word in title for word in ("question", "comparison")):
        return "Curiosity"
    if any(word in title for word in ("welcome", "benefit")):
        return "Excitement"
    if any(word in title for word in ("clarity", "information", "explain")):
        return "Confidence"
    return "Curiosity"


def _primary_visual(spec: PromptSpec) -> tuple[str, str]:
    """Turn a compact Brain tag into a scene a human designer can picture."""
    source = spec.objects.lower()
    if "smartphone" in source or "phone" in source:
        return (
            "An upright premium smartphone in a three-quarter view, occupying the right half of the frame. "
            "Its screen shows three large abstract interface cards with no tiny or unreadable UI copy; a soft shadow anchors it to the composition.",
            "the upright smartphone and its clear interface-card silhouette",
        )
    if "gift" in source:
        return (
            "A single premium gift box in the foreground with a wide satin ribbon in the lead accent colour. "
            "Use a gentle glow around the lid and a grounded shadow so it feels like a deliberate hero prop, not clip art.",
            "the glowing gift box",
        )
    if "megaphone" in source:
        return (
            "A sculptural, simplified megaphone angled upward from the lower side of the frame, with a subtle colour-gradient rim and a soft cast shadow. "
            "Keep it as one confident focal prop with no surrounding icon clutter.",
            "the angled sculptural megaphone",
        )
    if "bell" in source:
        return (
            "A single polished notification bell, enlarged and suspended above a quiet shadow, with a restrained halo that gives it depth. "
            "It should read as a clear notification cue rather than a collection of small app icons.",
            "the enlarged notification bell",
        )
    if "cloud" in source:
        return (
            "A small group of soft, layered cloud forms arranged as one sculptural visual cluster, with gentle depth and no busy sky scene. "
            "Place the cluster away from the copy so the headline remains the first readable element.",
            "the sculptural cloud cluster",
        )
    return (
        "An oversized, tactile headline panel is the hero visual, with a subtle layered edge and a single soft shadow. "
        f"Set it against a carefully controlled {spec.objects} treatment so the visual feels designed and dimensional, not like a flat colour fill.",
        "the oversized headline panel",
    )


def _visual_priority(primary_label: str) -> str:
    return "\n".join(
        [
            f"1. {primary_label}.",
            "2. The approved headline, set as the largest readable text element.",
            "3. The CTA, isolated in one clear high-contrast action area.",
        ]
    )


def _negative_prompt(season: str) -> str:
    seasonal = "- No snow, winter clothing, frost or Christmas styling for this summer direction.\n" if season.lower() == "summer" else ""
    return (
        seasonal
        + "- No extra words, slogans, disclaimers or unreadable pseudo-text beyond the approved headline and CTA.\n"
        "- No realistic banknotes, coins, casino symbols, gambling scenes, payout imagery or claims of financial outcomes.\n"
        "- No guarantees, refunds, no-loss claims, hidden conditions, fabricated reviews, badges or social-proof numbers.\n"
        "- No crowded collage, decorative icon cloud, excessive gradients, busy patterns, tiny type or low-contrast copy.\n"
        "- No distorted hands, warped devices, duplicate props, cut-off headline, cropped CTA, watermark or brand mark not supplied in the plan."
    )


def build_prompt(spec: PromptSpec) -> str:
    """Render an art-directed prompt using the matching GEO/funnel template."""
    template = template_path(spec.geo, spec.funnel).read_text(encoding="utf-8")
    primary_visual, primary_label = _primary_visual(spec)
    emotion = _emotion(spec)
    background = (
        f"Use a full-bleed {spec.colors} environment with a smooth tonal transition from the outer edges toward a quieter central reading area. "
        "Add only a restrained paper-like or studio-surface texture where it supports depth; leave generous negative space around the copy."
    )
    return template.format(
        number=f"{spec.number:03d}",
        geo=spec.geo,
        funnel=spec.funnel.title(),
        language=spec.geo,
        season=spec.season,
        style=spec.style,
        title=spec.title,
        priority=spec.priority,
        composition=spec.composition,
        headline=spec.headline,
        cta=spec.cta,
        references=spec.references,
        creative_goal=(
            f"Within the first 0.5 seconds, create {emotion.lower()} and make the approved message ‘{spec.headline}’ easy to understand without implying any outcome or reward."
        ),
        attention_hook=(
            f"Use the approved headline as oversized high-contrast type, immediately reinforced by {primary_label}."
        ),
        primary_visual=primary_visual,
        reading_flow=f"{spec.headline} → {primary_label} → {spec.cta}",
        visual_priority=_visual_priority(primary_label),
        emotion=emotion,
        typography=(
            "Set the headline in a bold sans-serif at roughly 112–148 px on the 1080 px canvas, using no more than two short lines. "
            "Set the CTA at roughly 44–56 px in a solid high-contrast button or pill. Keep at least 64 px clear space around the headline and CTA; no small print or condensed type."
        ),
        background=background,
        lighting=(
            "Use soft studio lighting with one controlled directional highlight on the primary visual and a subtle grounded shadow. "
            "Avoid harsh glare, dramatic lens effects or lighting that reduces text contrast."
        ),
        color_palette=(
            f"Build the palette from {spec.colors}. Reserve the strongest contrast for the headline and CTA, use one accent sparingly for focus, and keep all secondary areas calm."
        ),
        art_style=(
            f"{spec.style.title()} art direction: contemporary, intentional and editorial rather than generic stock-ad design. "
            f"Respect the approved composition: {spec.composition}."
        ),
        negative_prompt=_negative_prompt(spec.season),
        image_quality=(
            "Minimalistic, modern, premium, flat advertising banner, high readability, clean layout, high contrast and mobile-first. "
            "Deliver crisp edges, balanced spacing, polished 1080x1080 rendering and immediately legible hierarchy at phone size."
        ),
    )


def prompt_filename(spec: PromptSpec) -> str:
    return f"{spec.geo}-{spec.funnel}-{spec.number:03d}.prompt.md"
