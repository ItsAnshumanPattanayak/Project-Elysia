import json
import re
from typing import Literal

from pydantic import ValidationError

from app.ai.schemas import StructuredRoleplayResponse


def _candidate_json(text: str) -> str | None:
    stripped = text.strip()
    fence = re.fullmatch(r"```(?:json)?\s*(\{.*\})\s*```", stripped, re.DOTALL)
    if fence:
        return fence.group(1)
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    return None


def parse_roleplay_response(
    text: str,
) -> tuple[StructuredRoleplayResponse, Literal["structured", "plain_text_fallback"]]:
    candidate = _candidate_json(text)
    if candidate:
        try:
            value = StructuredRoleplayResponse.model_validate(json.loads(candidate))
            if not value.raw_text:
                value.raw_text = text
            return value, "structured"
        except (json.JSONDecodeError, ValidationError):
            pass

    narrations = [
        part.strip() for part in re.findall(r"\*([^*]+)\*", text) if part.strip()
    ]
    dialogue: list[str] = []
    for line in text.splitlines():
        match = re.match(r"\s*(?:Zara\s*:)?\s*[\"“](.*?)[\"”]\s*$", line)
        if match and match.group(1).strip():
            dialogue.append(match.group(1).strip())
    if not narrations and not dialogue and text.strip():
        dialogue = [text.strip()]
    return (
        StructuredRoleplayResponse(
            narration_blocks=narrations,
            dialogue_blocks=dialogue,
            raw_text=text,
        ),
        "plain_text_fallback",
    )
