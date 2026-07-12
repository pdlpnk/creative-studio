# Designer Agent v1

Designer Agent is the local hand-off between Creative Director and an image-generation tool. It reads the approved Creative Plan and creates one Markdown prompt for each hypothesis. It does not call an API, generate PNG files, perform QA or change Concept Cards.

## Input

- A Markdown Creative Plan created by `agents/creative_director/`.
- Its hypotheses, approved headline and CTA, colours, objects, composition, style, season and references to existing Concept Cards.

## Output

Prompts are written to `output/prompts/` as:

```text
TR-registration-001.prompt.md
TR-registration-002.prompt.md
```

The agent selects one template automatically:

- `registration_tr.md`
- `registration_az.md`
- `lead_tr.md`
- `lead_az.md`

Every prompt fixes the format at 1080x1080, records the GEO and banner language, contains only the approved banner copy, and adds composition, colours, objects, atmosphere, exclusions and image-quality requirements.

## Run directly

```bash
python3 agents/designer/designer.py plans/TR-registration-plan.md
```

## Use via Creative Studio CLI

```bash
python3 creative.py design --geo TR --funnel registration --count 20
```

This command first creates (or updates) the matching Creative Director plan, then makes the prompt files. To render an existing plan without replacing it, use `--plan`:

```bash
python3 creative.py design --plan plans/TR-registration-plan.md
```
