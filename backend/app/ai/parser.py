import json
import re
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import ValidationError

from app.ai.schemas import ParserDiagnostics, StructuredRoleplayResponse
from app.relationship.schemas import Mood, RelationshipEventType

MAX_RAW_OUTPUT = 50000
ParseStatus = Literal["structured", "repaired", "plain_text_fallback"]

EMOTION_ALIASES = {
    "loving": Mood.AFFECTIONATE,
    "concern": Mood.CONCERNED,
    "worried": Mood.CONCERNED,
    "protective concern": Mood.PROTECTIVE,
    "amused": Mood.PLAYFUL,
    "mad": Mood.ANGRY,
}
EVENT_ALIASES = {
    "support": RelationshipEventType.SUPPORTIVE,
    "supportive interaction": RelationshipEventType.SUPPORTIVE,
    "affection": RelationshipEventType.AFFECTIONATE,
    "romance": RelationshipEventType.ROMANTIC,
    "apology": RelationshipEventType.APOLOGETIC,
    "reassurance": RelationshipEventType.REASSURING,
    "conflict resolution": RelationshipEventType.CONFLICT_RESOLVED,
    "trust breach": RelationshipEventType.TRUST_BREACH,
}


@dataclass(frozen=True)
class ProcessedRoleplayResponse:
    response: StructuredRoleplayResponse
    parse_status: ParseStatus
    diagnostics: ParserDiagnostics


def _clean(text: str) -> str:
    return text.lstrip("\ufeff").strip()


def _extract_json(text: str) -> tuple[str, list[str]]:
    full_fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.I)
    if full_fence:
        return full_fence.group(1).strip(), ["removed_markdown_code_fence"]
    embedded = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.I)
    if embedded:
        return embedded.group(1).strip(), ["extracted_markdown_json_fence"]
    return text, []


def _safe_repair(text: str) -> tuple[str, list[str]]:
    repaired = re.sub(r",\s*([}\]])", r"\1", text)
    return repaired, ["removed_trailing_commas"] if repaired != text else []


def _canonical_mood(value: object) -> tuple[Mood | None, str | None]:
    if not isinstance(value, str) or not value.strip():
        return None, None
    original = value.strip()[:80]
    normalized = original.lower().replace("-", "_").replace(" ", "_")
    try:
        return Mood(normalized), None
    except ValueError:
        return EMOTION_ALIASES.get(original.lower()), original


def _canonical_event(value: object) -> tuple[RelationshipEventType | None, str | None]:
    if not isinstance(value, str) or not value.strip():
        return None, None
    original = value.strip()[:100]
    normalized = original.lower().replace("-", "_").replace(" ", "_")
    try:
        return RelationshipEventType(normalized), original
    except ValueError:
        return EVENT_ALIASES.get(original.lower()), original


def _strings(value: object, maximum: int) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value[:maximum]:
        if isinstance(item, str) and (cleaned := item.strip()):
            cleaned = cleaned[:2000]
            if cleaned not in result:
                result.append(cleaned)
    return result


def _normalize(value: dict[str, Any]) -> StructuredRoleplayResponse:
    allowed = {
        "narration_blocks",
        "dialogue_blocks",
        "emotion",
        "relationship_event",
        "memory_candidates",
        "raw_text",
    }
    if set(value) - allowed:
        raise ValueError("structured response contains unsupported fields")
    narration = _strings(value.get("narration_blocks"), 12)
    dialogue = _strings(value.get("dialogue_blocks"), 12)
    mood, original_mood = _canonical_mood(value.get("emotion"))
    event, original_event = _canonical_event(value.get("relationship_event"))
    raw_text = value.get("raw_text")
    if not isinstance(raw_text, str) or not raw_text.strip():
        parts = [*(f"*{item}*" for item in narration), *dialogue]
        raw_text = "\n\n".join(parts)
    memory_candidates = value.get("memory_candidates", [])
    return StructuredRoleplayResponse.model_validate(
        {
            "narration_blocks": narration,
            "dialogue_blocks": dialogue,
            "emotion": mood,
            "original_emotion": original_mood,
            "relationship_event": event,
            "model_relationship_suggestion": original_event,
            "memory_candidates": (
                memory_candidates if isinstance(memory_candidates, list) else []
            ),
            "raw_text": raw_text.strip()[:20000],
        }
    )


def _fallback(text: str, warnings: list[str]) -> ProcessedRoleplayResponse:
    safe_text = text[:20000]
    narrations = [
        part.strip()[:2000]
        for part in re.findall(r"\*([^*]+)\*", safe_text)
        if part.strip()
    ][:12]
    dialogue: list[str] = []
    for line in safe_text.splitlines():
        match = re.match(r'\s*(?:Zara\s*:)?\s*["“](.*?)["”]\s*$', line)
        if match and match.group(1).strip():
            dialogue.append(match.group(1).strip()[:2000])
    if not narrations and not dialogue and safe_text:
        dialogue = [safe_text[:2000]]
    response = StructuredRoleplayResponse(
        narration_blocks=narrations,
        dialogue_blocks=dialogue[:12],
        emotion=None,
        relationship_event=None,
        memory_candidates=[],
        raw_text=safe_text,
    )
    diagnostics = ParserDiagnostics(
        parse_status="plain_text_fallback",
        repair_attempted=False,
        schema_valid=False,
        fallback_used=True,
        warnings=warnings[:10],
    )
    return ProcessedRoleplayResponse(response, "plain_text_fallback", diagnostics)


def process_roleplay_response(text: str) -> ProcessedRoleplayResponse:
    if len(text) > MAX_RAW_OUTPUT:
        return _fallback(text[:MAX_RAW_OUTPUT], ["output_truncated_to_safe_limit"])
    cleaned = _clean(text)
    candidate, extraction_actions = _extract_json(cleaned)
    try:
        raw = json.loads(candidate)
        if not isinstance(raw, dict):
            raise TypeError("structured response is not an object")
        normalized = _normalize(raw)
        diagnostics = ParserDiagnostics(
            parse_status="structured",
            repair_actions=extraction_actions,
            schema_valid=True,
        )
        return ProcessedRoleplayResponse(normalized, "structured", diagnostics)
    except (json.JSONDecodeError, TypeError, ValueError, ValidationError):
        repaired, repair_actions = _safe_repair(candidate)
        if repair_actions:
            try:
                raw = json.loads(repaired)
                if not isinstance(raw, dict):
                    raise TypeError("structured response is not an object")
                normalized = _normalize(raw)
                actions = [*extraction_actions, *repair_actions]
                diagnostics = ParserDiagnostics(
                    parse_status="repaired",
                    repair_attempted=True,
                    repair_actions=actions,
                    schema_valid=True,
                    warnings=["Predictable JSON punctuation was repaired."],
                )
                return ProcessedRoleplayResponse(normalized, "repaired", diagnostics)
            except (json.JSONDecodeError, TypeError, ValueError, ValidationError):
                pass
    return _fallback(cleaned, ["structured_response_validation_failed"])


def parse_roleplay_response(
    text: str,
) -> tuple[StructuredRoleplayResponse, ParseStatus]:
    processed = process_roleplay_response(text)
    return processed.response, processed.parse_status
