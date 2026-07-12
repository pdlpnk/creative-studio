# Creative Director Agent

Creative Director is the first local decision-making agent in Creative Studio. It turns a user task such as “Create 20 Registration TR” into an evidence-based Markdown Creative Plan.

## Inputs

- Active Concept Cards from `brain/concepts/` through Creative Brain Search.
- Frequency, similarity, diversity and compliance signals from Creative Insights.
- Candidate combinations from Creative Generator, without creating generated cards or images.

## Output

Plans are saved in `plans/<GEO>-<funnel>-plan.md`.

Each plan contains goal, GEO, funnel, season, style, constraints, repetition warnings, overheated and rare ideas, and prioritised hypotheses. Every hypothesis cites existing `CC-*` source cards and a closest active-card similarity score.

## Run directly

```bash
python3 agents/creative_director/director.py --geo TR --funnel registration --count 20
```

Or use the unified CLI:

```bash
python3 creative.py plan --geo TR --funnel registration --count 20
```

## Limits

- The agent uses no API, internet connection or image generation.
- It does not modify active Concept Cards or generated drafts.
- Recommendations are based on local metadata diversity, not predicted campaign performance.
- Compliance notes identify review needs; they are not a legal determination.
