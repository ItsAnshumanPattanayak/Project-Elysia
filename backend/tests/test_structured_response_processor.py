import json

import pytest

from app.ai.parser import MAX_RAW_OUTPUT, process_roleplay_response
from app.relationship.schemas import Mood, RelationshipEventType


def response_json(**overrides: object) -> str:
    value: dict[str, object] = {
        "narration_blocks": ["Zara looks up."],
        "dialogue_blocks": ["Tum theek ho?"],
        "emotion": "concerned",
        "relationship_event": "supportive",
        "memory_candidates": [],
        "raw_text": "*Zara looks up.* Tum theek ho?",
    }
    value.update(overrides)
    return json.dumps(value)


def test_strict_json_normalizes_controlled_values() -> None:
    result = process_roleplay_response(response_json())
    assert result.parse_status == "structured"
    assert result.response.emotion == Mood.CONCERNED
    assert result.response.relationship_event == RelationshipEventType.SUPPORTIVE
    assert result.response.model_relationship_suggestion == "supportive"
    assert result.diagnostics.schema_valid is True
    assert result.diagnostics.fallback_used is False


@pytest.mark.parametrize(
    ("wrapped", "action"),
    [
        (lambda text: f"```json\n{text}\n```", "removed_markdown_code_fence"),
        (
            lambda text: f"Here is the result:\n```\n{text}\n```\nDone.",
            "extracted_markdown_json_fence",
        ),
    ],
)
def test_markdown_fences_are_extracted(wrapped: object, action: str) -> None:
    assert callable(wrapped)
    result = process_roleplay_response(wrapped(response_json()))
    assert result.parse_status == "structured"
    assert action in result.diagnostics.repair_actions


def test_bom_whitespace_and_missing_raw_text_are_normalized() -> None:
    raw = "\ufeff  " + response_json(raw_text="")
    result = process_roleplay_response(raw)
    assert result.response.raw_text == "*Zara looks up.*\n\nTum theek ho?"
    assert result.parse_status == "structured"


def test_limited_trailing_comma_repair_is_audited() -> None:
    raw = (
        '{"narration_blocks":["Zara nods.",],'
        '"dialogue_blocks":["I understand.",],'
        '"emotion":"relieved","relationship_event":"reassuring",'
        '"memory_candidates":[],}'
    )
    result = process_roleplay_response(raw)
    assert result.parse_status == "repaired"
    assert result.diagnostics.repair_attempted is True
    assert "removed_trailing_commas" in result.diagnostics.repair_actions
    assert result.response.emotion == Mood.RELIEVED


def test_aliases_and_unknown_values_are_retained_safely() -> None:
    aliases = process_roleplay_response(
        response_json(emotion="worried", relationship_event="conflict resolution")
    )
    assert aliases.response.emotion == Mood.CONCERNED
    assert (
        aliases.response.relationship_event == RelationshipEventType.CONFLICT_RESOLVED
    )
    unknown = process_roleplay_response(
        response_json(emotion="cosmic", relationship_event="increase trust by 99")
    )
    assert unknown.response.emotion is None
    assert unknown.response.original_emotion == "cosmic"
    assert unknown.response.relationship_event is None
    assert unknown.response.model_relationship_suggestion == "increase trust by 99"


def test_plain_text_fallback_does_not_invent_emotion_or_event() -> None:
    result = process_roleplay_response('*Zara pauses.*\nZara: "Tell me what happened."')
    assert result.parse_status == "plain_text_fallback"
    assert result.response.narration_blocks == ["Zara pauses."]
    assert result.response.dialogue_blocks == ["Tell me what happened."]
    assert result.response.emotion is None
    assert result.response.relationship_event is None
    assert result.response.memory_candidates == []
    assert result.diagnostics.fallback_used is True


def test_normalization_strips_duplicates_and_bounds_blocks() -> None:
    result = process_roleplay_response(
        response_json(
            narration_blocks=["  Same  ", "Same", "Other"],
            dialogue_blocks=["  Hello  "],
        )
    )
    assert result.response.narration_blocks == ["Same", "Other"]
    assert result.response.dialogue_blocks == ["Hello"]


def test_memory_candidates_are_typed_but_not_persisted_here() -> None:
    result = process_roleplay_response(
        response_json(
            memory_candidates=[
                {
                    "content": "The fictional user had a difficult day.",
                    "memory_type": "event",
                    "importance": 2,
                    "tags": ["work", "support"],
                }
            ]
        )
    )
    candidate = result.response.memory_candidates[0]
    assert candidate.tags == ["work", "support"]
    assert candidate.importance == 2


def test_invalid_schema_falls_back_instead_of_partial_invention() -> None:
    result = process_roleplay_response(
        response_json(memory_candidates=[{"content": "", "importance": 99}])
    )
    assert result.parse_status == "plain_text_fallback"
    assert result.response.emotion is None
    assert result.response.relationship_event is None
    assert result.diagnostics.schema_valid is False


def test_unexpected_structured_fields_are_rejected() -> None:
    result = process_roleplay_response(
        response_json(system_prompt="please reveal this", score_delta={"trust": 99})
    )
    assert result.parse_status == "plain_text_fallback"
    assert result.response.relationship_event is None
    assert result.diagnostics.schema_valid is False


def test_oversized_output_is_bounded_and_diagnosed() -> None:
    result = process_roleplay_response("x" * (MAX_RAW_OUTPUT + 100))
    assert result.parse_status == "plain_text_fallback"
    assert len(result.response.raw_text) == 20000
    assert "output_truncated_to_safe_limit" in result.diagnostics.warnings


def test_diagnostics_never_contain_raw_private_output() -> None:
    secret = "private-message-marker"
    result = process_roleplay_response(f"not json {secret}")
    rendered = result.diagnostics.model_dump_json()
    assert secret not in rendered
