# Creative Analyzer v2: Image Analysis Architecture

## Purpose

Creative Analyzer v2 defines the future architecture for turning one reference image into a structured Creative Concept Card. Its output is a Markdown file saved in `brain/concepts/`.

This document specifies the data contract, component boundaries, validation rules and output format only. It does not analyse images, contain OpenAI code, call any API, add libraries or implement an executable tool.

## Scope

Input:

- one static image from `assets/references/`;
- its relative path, filename, extension, checksum and filesystem metadata;
- optional context inferred from its directory, such as `geo` and `funnel`.

Output:

- one reviewable Markdown Concept Card at `brain/concepts/<id>.md`;
- a structured record containing all fields in this specification;
- an explicit analysis status and provenance for human review.

The analyser must not modify, rename, recompress or delete the source image.

## System boundaries

```text
Reference image
    ↓
Input & metadata adapter
    ↓
Future vision-analysis provider
    ↓
Normalizer and schema validator
    ↓
Compliance and confidence review
    ↓
Concept Card renderer
    ↓
brain/concepts/CC-NNNN.md
```

Each stage has a narrow interface. The future vision-analysis provider is replaceable: it may later be backed by an AI service, but it must return the schema below and never write files or assign IDs itself.

## Component interfaces

| Component | Receives | Produces | Responsibility |
|---|---|---|---|
| Input & metadata adapter | Source path | Immutable image reference and technical metadata | Confirms supported extension, reads filename, hash, date and path-derived context. |
| ID allocator | Existing Concept Card IDs | Next unused `CC-NNNN` | Reserves an ID without reusing or overwriting an existing card. |
| Future vision-analysis provider | Image reference and analysis schema | Raw structured observations | Describes visible visual and copy evidence; no filesystem or network implementation is defined here. |
| Normalizer | Raw observations | Controlled field values | Normalizes enum values, arrays, empty values, scores and language labels. |
| Validator | Normalized analysis | Valid result or review errors | Enforces required fields, score ranges, provenance and output safety. |
| Compliance reviewer | Copy, offer and claims | Approved, flagged or review-required result | Flags misleading promises, guaranteed outcomes, hidden terms and fabricated proof. |
| Concept Card renderer | Validated record | Markdown text | Renders the documented output shape without changing the source image. |
| Writer | Markdown text and target ID | New Concept Card file | Atomically saves `brain/concepts/<id>.md`; never overwrites a card. |

## Analysis record

Every record contains the following groups. Values inferred from image content must be distinguishable from path metadata and must be reviewable by a human.

### General

| Field | Type | Source / rule |
|---|---|---|
| `id` | text | Unique Concept ID: `CC-NNNN`. |
| `filename` | text | Original filename, preserved exactly. |
| `hash` | text | SHA-256 checksum of source bytes. |
| `date` | datetime | Source modification time or import time, with provenance. |
| `geo` | enum / unknown | `TR`, `AZ` or `unknown`; directory metadata takes priority when unambiguous. |
| `funnel` | enum / unknown | `registration`, `lead` or `unknown`; directory metadata takes priority when unambiguous. |
| `language` | enum / unknown | Primary visible copy language: `TR`, `AZ`, `mixed` or `unknown`. |
| `creative_type` | text | Concise category, for example `static promotional banner`, `mobile UI creative` or `informational card`. |

### Visual

| Field | Type | Description |
|---|---|---|
| `primary_colors` | list | Dominant visual colours, ideally with HEX values when reliable. |
| `accent_colors` | list | Supporting or CTA accent colours. |
| `background` | text | Background colour, texture, gradient, scene or treatment. |
| `composition` | text | Main arrangement and visual balance. |
| `layout` | text | Placement of headline, product, CTA, logo and supporting elements. |
| `perspective` | text | Flat, front-facing, isometric, close-up, angled or unknown. |
| `objects` | list | Visible product and contextual objects. |
| `phone_present` | boolean | Whether a phone is visibly present. |
| `gift_present` | boolean | Whether a gift or gift box is visibly present. |
| `coins_present` | boolean | Whether coins, money symbols or coin imagery is visibly present. |
| `person_present` | boolean | Whether a person is visibly present. |
| `icons` | list | Visible icons, symbols or UI indicators. |
| `cta_button` | text / none | CTA button appearance, copy and location; use `none` if absent. |
| `typography` | text | Font style, casing, text treatment and hierarchy. |
| `font_weight` | text | Dominant apparent weight: light, regular, medium, bold, heavy or mixed. |
| `contrast` | text | Text/background and key-element contrast assessment. |
| `spacing` | text | Density, margins, whitespace and alignment. |
| `visual_complexity` | enum | `low`, `medium` or `high`. |
| `emotion` | list | Perceived intended emotions, for example trust, urgency, friendly or premium. |

### Copy

| Field | Type | Description |
|---|---|---|
| `headline` | text / empty | Main visible headline; preserve wording and mark unreadable text rather than guessing. |
| `subheadline` | text / empty | Supporting headline or explanatory copy. |
| `offer` | text / empty | Visible offer, including conditions if visible. |
| `cta` | text / empty | Visible call to action. |
| `numbers` | list | Every visible meaningful number with its context. |
| `currency` | list | Currency indicators visible in the image. |
| `language_quality` | text | Apparent grammar, naturalness and localisation quality; `review_required` if uncertain. |
| `readability` | text | Legibility of copy at the intended viewing size. |

### Marketing

| Field | Type | Description |
|---|---|---|
| `audience` | text | Inferred intended audience; qualify as an inference when not explicit. |
| `pain` | text / empty | Problem or concern addressed by the creative. |
| `desire` | text / empty | Desired outcome or motivation appealed to. |
| `hook` | text / empty | Primary attention mechanism. |
| `trust_elements` | list | Visible trust indicators, disclosures, brand signals, ratings or support cues. |
| `urgency` | text / none | Time pressure or scarcity mechanism; `none` when absent. |
| `social_proof` | text / none | Testimonial, usage signal or rating only when visibly supported; `none` when absent. |
| `value_proposition` | text / empty | Clear description of offered value without adding unsupported claims. |

### Design score

All scores are integer assessments from `1` to `5`. A score is a review aid, not a performance prediction.

| Field | Meaning |
|---|---|
| `composition` | Balance, focus and arrangement of visual elements. |
| `readability` | Ease of reading visible copy. |
| `contrast` | Separation of text and important visual elements. |
| `hierarchy` | Clarity of attention order. |
| `cta_visibility` | Ease of finding and understanding the CTA. |
| `offer_visibility` | Ease of identifying the offer and material conditions. |
| `overall` | Holistic design-quality assessment, not a marketing outcome forecast. |

### Production notes

| Field | Description |
|---|---|
| `why_it_may_work` | Evidence-based explanation of why the banner may attract attention or communicate its message. |
| `weaknesses` | Visible weaknesses, ambiguities, accessibility risks or compliance risks. |
| `test_ideas` | Isolated, measurable ideas for future A/B testing. |
| `changes` | Concrete elements that could be changed in a future variation. |
| `keep` | Elements worth preserving in a future variation. |

## Required output format

The future renderer creates `brain/concepts/<id>.md`. The following is the required independent output shape; empty or uncertain values must be explicit rather than invented.

```markdown
---
id: CC-0000
name: ""
source:
  filename: ""
  asset_path: ""
  hash: ""
  date: ""
  date_source: ""
general:
  geo: unknown
  funnel: unknown
  language: unknown
  creative_type: ""
visual:
  primary_colors: []
  accent_colors: []
  background: ""
  composition: ""
  layout: ""
  perspective: unknown
  objects: []
  phone_present: false
  gift_present: false
  coins_present: false
  person_present: false
  icons: []
  cta_button: none
  typography: ""
  font_weight: mixed
  contrast: ""
  spacing: ""
  visual_complexity: medium
  emotion: []
copy:
  headline: ""
  subheadline: ""
  offer: ""
  cta: ""
  numbers: []
  currency: []
  language_quality: review_required
  readability: ""
marketing:
  audience: ""
  pain: ""
  desire: ""
  hook: ""
  trust_elements: []
  urgency: none
  social_proof: none
  value_proposition: ""
design_score:
  composition: null
  readability: null
  contrast: null
  hierarchy: null
  cta_visibility: null
  offer_visibility: null
  overall: null
analysis_status: pending_review
analysis_provenance:
  provider: future_adapter
  provider_version: ""
  schema_version: creative-analyzer-v2
  reviewed_by: ""
  reviewed_at: ""
---

# Summary

Short factual description of the visible creative.

# Why it may work

Evidence-based rationale. Do not claim performance certainty.

# Weaknesses

Visible design, clarity or compliance risks.

# Test ideas

One variable per proposed test.

# Changes

Specific changes for a future variation.

# Keep

Elements worth retaining.
```

## Validation and safety rules

- `id` must be unique and the filename must be `<id>.md`.
- `filename` and `hash` are required before a card can be saved.
- `hash` must be the SHA-256 value of the unchanged source file.
- `date_source` must identify whether `date` came from filesystem metadata or the import process.
- Boolean visual-presence fields accept only `true` or `false`.
- `visual_complexity` accepts only `low`, `medium` or `high`.
- Every non-null design score must be an integer from `1` to `5`.
- Unreadable or uncertain copy must be marked as uncertain; the analyser must not invent text.
- Inferences about audience, pain, desire and performance must be framed as inferences, not facts.
- A result cannot be marked `processed` before human review.
- The analysis must not introduce unsupported promises, guaranteed income or winnings, hidden conditions, false testimonials or fabricated social proof.
- The source image must never be altered by any stage.

## Future provider contract

When an AI-capable provider is introduced in a later, separately approved task, it must satisfy this contract:

1. Receive an immutable image reference and this schema version.
2. Return structured observations for every group above, including explicit uncertainty.
3. Preserve visible copy verbatim where legible; do not manufacture unreadable text.
4. Provide no direct filesystem writes, ID allocation or status changes.
5. Return provenance sufficient to reproduce or audit the analysis.
6. Allow the validator and human reviewer to reject any field.

No API, model, library or provider implementation is part of Creative Analyzer v2 architecture.
