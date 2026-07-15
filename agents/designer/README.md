# Designer Agent v1

Designer Agent is the local art-direction hand-off between Creative Director and an image-generation tool. It reads the approved Creative Plan and creates one Markdown prompt for each hypothesis. It turns compact Brain tags into a concrete visual scene and hierarchy; it does not call an API, generate PNG files, perform QA or change Concept Cards.

Visual Library v1 in `visual_library/` provides the permitted hooks, detailed scene objects, patterns, compositions, palettes, backgrounds and emotions. Designer chooses one hook, one pattern and one composition per prompt and limits supporting objects to two. Restricted concepts such as cashback, crypto, USDT, membership, sports or a large number are not added unless the input confirms them.

Marketing Library in `marketing_library/` now supplies the first decision. Designer follows this order: Creative Idea → Marketing Hook → Emotion → Visual Trigger → Primary Object → Supporting Objects → Composition → Visual Style → Final Prompt. It does not select a phone, gift or notification as decoration; every visual trigger must be recommended by the selected marketing hook. A batch interleaves compliant hooks so diversity appears from the first concepts.

## Input

- A Markdown Creative Plan created by `agents/creative_director/`.
- Its hypotheses, approved headline and CTA, colours, composition, style, season and references to existing Concept Cards.

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

Every prompt fixes the format at 1080x1080, records the GEO and banner language, and contains only the approved banner copy. Its concise art-direction sections are:

- Creative Intent, Audience and Approved Text;
- Primary Hook, Scene and Composition;
- Visual Style, Must Avoid and Output.

Primary Visual is written as a complete scene, not as an isolated label such as `smartphone` or `megaphone`.

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
