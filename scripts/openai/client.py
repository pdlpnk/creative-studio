"""OpenAI Responses API adapter for static-image analysis."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI, RateLimitError

from config import OpenAISettings, load_settings


SUPPORTED_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


class VisionAdapterError(RuntimeError):
    """Base error for recoverable Vision Adapter failures."""


class ImageFileError(VisionAdapterError):
    """Raised when an input image is missing or unsupported."""


class VisionTimeoutError(VisionAdapterError):
    """Raised when the API request exceeds its configured timeout."""


class VisionRateLimitError(VisionAdapterError):
    """Raised when the API reports a rate or quota limit."""


class VisionAPIError(VisionAdapterError):
    """Raised when the API cannot complete the request."""


class EmptyVisionResponseError(VisionAdapterError):
    """Raised when the API response contains no text output."""


class InvalidVisionResponseError(VisionAdapterError):
    """Raised when the prompt-required JSON cannot be decoded."""


class OpenAIVisionClient:
    """Send one local image and one analysis prompt to the Responses API.

    ``analyze_image`` returns a decoded JSON object. The caller controls the
    prompt and can therefore version the expected response schema separately.
    """

    def __init__(self, settings: OpenAISettings | None = None) -> None:
        self.settings = settings or load_settings()
        self._client = OpenAI(
            api_key=self.settings.api_key,
            timeout=self.settings.timeout_seconds,
            max_retries=0,
        )

    @staticmethod
    def _image_data_url(image_path: Path) -> str:
        image_path = image_path.expanduser().resolve()
        if not image_path.is_file():
            raise ImageFileError(f"Image file not found: {image_path}")

        mime_type = SUPPORTED_MIME_TYPES.get(image_path.suffix.lower())
        if not mime_type:
            extensions = ", ".join(sorted(SUPPORTED_MIME_TYPES))
            raise ImageFileError(
                f"Unsupported image format: {image_path.suffix or 'no extension'}. "
                f"Supported: {extensions}"
            )

        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        return f"data:{mime_type};base64,{encoded}"

    def analyze_image(self, image_path: str | Path, prompt: str) -> dict[str, Any]:
        """Return the structured model response for a supported local image.

        The supplied prompt must instruct the model to return a JSON object.
        No source image is modified, uploaded to a repository or logged.
        """
        if not prompt or not prompt.strip():
            raise ValueError("Analysis prompt must not be empty.")

        data_url = self._image_data_url(Path(image_path))
        try:
            response = self._client.responses.create(
                model=self.settings.model,
                input=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": prompt},
                            {"type": "input_image", "image_url": data_url},
                        ],
                    }
                ],
            )
        except APITimeoutError as error:
            raise VisionTimeoutError(
                "OpenAI request timed out. Retry later or increase OPENAI_TIMEOUT."
            ) from error
        except RateLimitError as error:
            raise VisionRateLimitError(
                "OpenAI rate or quota limit reached. Retry later or review account limits."
            ) from error
        except APIConnectionError as error:
            raise VisionAPIError(
                "Could not connect to the OpenAI API. Check network access and retry."
            ) from error
        except APIStatusError as error:
            raise VisionAPIError(
                f"OpenAI API returned HTTP {error.status_code}. Retry or inspect the request."
            ) from error
        except Exception as error:
            raise VisionAPIError("OpenAI API request failed unexpectedly.") from error

        output_text = getattr(response, "output_text", "")
        if not output_text or not output_text.strip():
            raise EmptyVisionResponseError("OpenAI returned an empty text response.")

        try:
            parsed = json.loads(output_text)
        except json.JSONDecodeError as error:
            raise InvalidVisionResponseError(
                "OpenAI response was not valid JSON. Ensure the prompt requests one JSON object."
            ) from error
        if not isinstance(parsed, dict):
            raise InvalidVisionResponseError("OpenAI response JSON must be an object.")
        return parsed
