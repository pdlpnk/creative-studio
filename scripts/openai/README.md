# OpenAI Vision Adapter

OpenAI Vision Adapter is the independent AI boundary for Creative Studio. Any future module can instantiate `OpenAIVisionClient` and call `analyze_image(image_path, prompt)` to send one static image to the OpenAI Responses API and receive a decoded JSON object.

The adapter does not create Concept Cards, change queue state, modify source images or call the Concept Generator.

## Supported image formats

- `.jpg`
- `.jpeg`
- `.png`
- `.webp`

## Install dependencies

The adapter uses the official OpenAI Python SDK:

```bash
python3 -m pip install openai
```

## Configure `.env`

Create a `.env` file in the repository root. It is ignored by Git.

```dotenv
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-5.5
OPENAI_TIMEOUT=120
```

Never place a real key in code, documentation, prompt files or a Concept Card. An environment variable takes precedence over `.env`.

## Example call

Run from the repository root:

```python
from pathlib import Path
import sys

sys.path.insert(0, "scripts/openai")
from client import OpenAIVisionClient

prompt = """Return one JSON object with a short description of the visible image."""
client = OpenAIVisionClient()
result = client.analyze_image(
    Path("assets/references/registration/tr/1gpt promo.png"),
    prompt,
)
print(result)
```

## Example response

The adapter decodes the model output into a Python dictionary. The exact shape is defined by the prompt supplied by the caller.

```json
{
  "general": {
    "language": "TR",
    "creative_type": "static promotional banner"
  },
  "visual": {
    "primary_colors": ["blue", "white"],
    "phone_present": true
  }
}
```

## Error handling

`analyze_image` raises explicit errors for:

- absent or unsupported files (`ImageFileError`);
- missing configuration (`ConfigurationError`);
- timeouts (`VisionTimeoutError`);
- rate/quota limits (`VisionRateLimitError`);
- connection and API-status failures (`VisionAPIError`);
- empty or non-JSON model output (`EmptyVisionResponseError`, `InvalidVisionResponseError`).

The adapter disables SDK retries (`max_retries=0`) so the caller owns retry policy and can avoid duplicate work.

## API design

The adapter Base64-encodes a local image as a data URL and submits it as an `input_image` item to `client.responses.create`. This follows the official OpenAI [Images and vision guide](https://developers.openai.com/api/docs/guides/images-vision) and the [Responses API guide](https://developers.openai.com/api/docs/guides/responses).

The prompt must require one JSON object. For the Creative Analyzer schema, use `scripts/concept_generator/prompt.md` from a caller; this adapter deliberately does not import or invoke that module.
