# Creative Insights v1

Creative Insights v1 is a fully local analytics layer over [Creative Brain Search](../search/README.md). It reads existing Concept Cards through `brain/search/index.py`; it does not call OpenAI, Claude, a browser, or any internet service.

## Run

From the repository root:

```bash
python3 brain/insights/insights.py
```

For the complete machine-readable report:

```bash
python3 brain/insights/insights.py --json
```

## Report sections

- **General analytics** — card count; GEO, funnel and language distributions; average available design and readability scores.
- **Frequency analysis** — observed TOP CTA, headline tokens, colours, objects, bonus-like phrases, offers and composition descriptions.
- **Similarity analysis** — structurally similar cards plus lexical similarities in copy, offers and exact CTAs.
- **Diversity analysis** — repeated ideas, rare colours/objects and absent combinations of observed GEO, funnel and colour values.
- **Compliance analysis** — cards whose visible indexed copy contains local keyword matches for guarantees, refunds, no-risk language or verification terms.
- **Opportunity report** — data-dependent experiment directions built from the current counts and gaps.

## Method and limits

Insights are local heuristics, not performance claims:

- Similarity uses Jaccard overlap of existing text and visual metadata.
- “Semantic duplicates” means lexical copy overlap, not a model-generated semantic judgement.
- Compliance output is a review queue triggered by words and phrases; it is not legal advice or a final policy decision.
- Recommendations are emitted only when their underlying condition is present in the current index.
- No result predicts CTR, conversion rate, revenue or campaign outcome.
