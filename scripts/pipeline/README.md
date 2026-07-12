# Creative Pipeline v1

Creative Pipeline v1 is the first end-to-end Creative Studio workflow for one image. It reuses existing modules and introduces no new analysis, parsing or rendering logic.

## Flow

```text
image path
   ↓
OpenAIVisionClient.analyze_image(image_path, prompt)
   ↓
scripts/concept_generator/prompt.md
   ↓
structured JSON model response
   ↓
scripts/concept_generator/parser.py
   ↓
brain/concepts/CC-XXXX.md
```

The pipeline does not call the Creative Queue and does not modify it. It also does not modify the Concept Generator or OpenAI adapter.

## Run

From the repository root:

```bash
python3 scripts/pipeline/pipeline.py assets/references/registration/tr/1gpt\ promo.png
```

The OpenAI adapter loads `OPENAI_API_KEY` from the environment or the repository-root `.env`. See [`scripts/openai/README.md`](../openai/README.md) for SDK installation and configuration.

On successful creation, the command prints:

```text
SUCCESS
ID: CC-0003
Path: brain/concepts/CC-0003.md
```

The ID shown is an example; the pipeline allocates the next available Concept ID.

## Failure behaviour

- Missing API key: prints a clear configuration error and exits without creating a card.
- Empty model response: stops before the parser is called and creates no card.
- Vision API, timeout, rate-limit, missing-image or invalid-JSON error: stops before the parser is called and creates no card.
- Invalid parser response: stops without producing a valid card.

Cards are written only after the Vision Adapter returns a non-empty structured JSON object. Existing cards are never overwritten.
