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


def build_prompt(spec: PromptSpec) -> str:
    """Render one prompt using the matching GEO/funnel template."""
    template = template_path(spec.geo, spec.funnel).read_text(encoding="utf-8")
    return template.format(
        number=f"{spec.number:03d}",
        geo=spec.geo,
        funnel=spec.funnel.title(),
        language=spec.geo,
        season=spec.season,
        style=spec.style,
        title=spec.title,
        priority=spec.priority,
        colors=spec.colors,
        objects=spec.objects,
        composition=spec.composition,
        headline=spec.headline,
        cta=spec.cta,
        references=spec.references,
    )


def prompt_filename(spec: PromptSpec) -> str:
    return f"{spec.geo}-{spec.funnel}-{spec.number:03d}.prompt.md"
