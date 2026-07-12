# Creative Concept Generator v1

Creative Concept Generator v1 is a working local CLI that creates draft Markdown Concept Cards from a single image or a folder of images. It currently uses a deterministic `MOCK` provider: no image pixels are analysed, no API request is made and no external Python packages are required.

The module is deliberately split into a provider boundary (`analyze_image`), a prompt, and a parser/renderer so that a future OpenAI vision implementation can replace the MOCK without changing the CLI or Markdown output contract.

## Files

| File | Purpose |
|---|---|
| `main.py` | CLI, image discovery, ID allocation and the replaceable `analyze_image` provider boundary. |
| `parser.py` | Validates a structured provider response and writes a new Concept Card to `brain/concepts/`. |
| `prompt.md` | Versioned analysis instruction and JSON response contract for a future vision provider. |

## Run

Run from the repository root:

```bash
python scripts/concept_generator/main.py path/to/image.png
python scripts/concept_generator/main.py assets/references/lead/tr/
```

The generator accepts `.jpg`, `.jpeg`, `.png` and `.webp` files. It processes folders recursively and creates one card per supported image as `brain/concepts/CC-XXXX.md`.

Use `--dry-run` to verify discovery and planned output paths without creating cards:

```bash
python scripts/concept_generator/main.py assets/references/registration/tr --dry-run
```

The program finds the largest existing `CC-XXXX` value anywhere under `brain/concepts/` and uses the next value. Existing cards are never overwritten.

## Current MOCK behaviour

`analyze_image(image_path)` returns a complete structured response with:

- source filename, SHA-256 checksum, modification date, and path-derived GEO/funnel where reliable;
- explicit placeholder values for visual, copy and marketing fields;
- `analysis_status: pending_review`;
- no generated claims, no image-content interpretation, and no network activity.

The result is rendered by `parser.py` into YAML front matter and Markdown sections covering General, Visual, Copy, Marketing, Design Score and Production Notes.

## Replacing MOCK with OpenAI Responses API later

Do this only in a separately approved change that adds the OpenAI Python SDK and provides `OPENAI_API_KEY` through the environment or another secret manager. Never store an API key in this repository, a Concept Card or a prompt file.

1. Keep the public function signature `analyze_image(image_path: Path) -> dict[str, Any]`.
2. Load `prompt.md` as the analysis instruction.
3. Encode the local image as an image input accepted by the Responses API, together with source metadata.
4. Request a structured JSON response matching the exact schema in `prompt.md`.
5. Pass the returned JSON object unchanged to `save_concept_card`.
6. Preserve parser validation, `pending_review`, atomic non-overwriting writes and human compliance review.

The Responses API supports multimodal image inputs, and OpenAI documents vision inputs and the Responses API in its official guides: [Images and vision](https://developers.openai.com/api/docs/guides/images-vision) and [Responses API](https://developers.openai.com/api/docs/guides/responses). Confirm the current SDK method, model and structured-output settings at implementation time rather than copying an old snippet.

## Safety and limits

- The MOCK does not analyse the source image.
- Cards are drafts and remain subject to human review.
- `winner` and `loser` are never assigned by this tool.
- No claim should be generated unless it is verifiable from the source and approved by a responsible person.
- The generator never modifies, renames or deletes input images.
