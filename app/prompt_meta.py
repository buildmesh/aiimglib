"""Shared helpers for validating prompt metadata structures."""
from __future__ import annotations

from typing import Union

PromptMetaType = Union[dict, list, str, None]


class PromptMetaFormatError(ValueError):
    """Raised when prompt metadata is in an invalid shape."""


def validate_prompt_meta_structure(value: PromptMetaType) -> PromptMetaType:
    """Ensure prompt metadata matches the `[refs..., text]` contract."""
    if value is None or isinstance(value, (str, dict)):
        return value
    if isinstance(value, list):
        if not value:
            raise PromptMetaFormatError(
                "prompt reference lists must include a trailing prompt string"
            )
        *references, prompt_text = value
        if not isinstance(prompt_text, str):
            raise PromptMetaFormatError(
                "prompt reference lists must end with the prompt text string"
            )
        for ref in references:
            if not isinstance(ref, dict) or set(ref.keys()) != {"id"}:
                raise PromptMetaFormatError(
                    "prompt references must be objects containing only an 'id' field"
                )
            ref_id = ref["id"]
            if not isinstance(ref_id, str) or not ref_id:
                raise PromptMetaFormatError(
                    "prompt reference ids must be non-empty strings"
                )
        return value
    raise PromptMetaFormatError(
        "prompt metadata must be a string, dict, or prompt reference list"
    )


def extract_prompt_text(value: PromptMetaType) -> str:
    """Return the prompt text from metadata structures for storage."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        validate_prompt_meta_structure(value)
        return value[-1]
    if isinstance(value, dict):
        # Legacy metadata dictionaries may carry additional info without text.
        return ""
    raise PromptMetaFormatError(
        "prompt metadata must be a string, dict, or prompt reference list"
    )
