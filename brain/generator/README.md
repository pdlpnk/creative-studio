# Creative Generator v1

Creative Generator v1 creates safe, local draft Concept Cards from the existing Creative Brain and Creative Insights data. It uses no OpenAI API, internet access or image generation.

## Inputs

- `assets/references/` remains the reference archive; the generator does not modify it.
- `brain/concepts/` supplies active Concept Cards through Creative Brain.
- `brain/search/` supplies normalized card fields and local similarity inputs.
- `brain/insights/` supplies frequency, diversity and opportunity signals.

## Output

Generated drafts are written to `brain/generated/CG-NNNN.md`. They stay outside `brain/concepts/` until human review promotes them.

Every draft includes General, Visual, Copy, Marketing, Compliance, Production Notes and Design Score sections, plus:

- `generated_from` source-card IDs;
- `novelty_score` from 0–100, calculated from the inverse of maximum local feature similarity;
- `similarity_to_existing` with the closest active card and Jaccard score;
- `generation_key`, used to avoid repeated plans on later runs.

## Method

The generator reads Insights diversity gaps, especially untested GEO/funnel/colour combinations, then combines them with observed colours and objects. It uses deterministic information-led layouts and cautious localised draft copy.

Generated copy avoids bonus, refund, guarantee, no-loss, income and urgency claims. It is a design draft, not a performance prediction; human review remains required for final localisation, offer accuracy and compliance.

## Run

From the repository root:

```bash
python3 brain/generator/generator.py
```

The default command creates 20 new cards. To request another number:

```bash
python3 brain/generator/generator.py --count 5
```

The CLI reports the created count, highest novelty drafts, risk ranking, closest existing cards and which drafts should go to design first.

## Limits

- Novelty is structural metadata novelty, not expected advertising performance.
- Similarity is local Jaccard overlap of colours, objects, offer, CTA and composition tokens.
- Design scores are planned visual-review targets, not measured results.
- The module does not create images or change existing Concept Cards.
