import re
from collections.abc import Iterable

from app.ai.schemas import MemoryCandidate
from app.core.config import Settings
from app.memory.normalization import display_content, normalize_content, normalize_tags
from app.memory.schemas import NormalizedCandidate
from app.memory.types import MemorySource, MemoryType

SECRET_RE = re.compile(
    r"(?i)(password|passwd|api[_ -]?key|access[_ -]?token|secret)\s*[:=]\s*\S+"
)
PATH_RE = re.compile(r"(?i)(?:[a-z]:\\|/(?:home|users|etc|var)/)")
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d ()-]{8,}\d)(?!\d)")
QUESTION_RE = re.compile(r"\?\s*$")
HYPOTHETICAL_RE = re.compile(r"(?i)\b(maybe|perhaps|if i|suppose|pretend|might)\b")
QUOTED_RE = re.compile(r"^\s*[\"“']|[\"”']\s*$")
GENERIC = {"hello", "hi", "hey", "okay", "ok", "thank you", "thanks", "yes", "no"}

ALIASES = {
    "preference": MemoryType.USER_PREFERENCE,
    "dislike": MemoryType.USER_DISLIKE,
    "goal": MemoryType.USER_GOAL,
    "habit": MemoryType.USER_HABIT,
    "boundary": MemoryType.USER_BOUNDARY,
    "event": MemoryType.SHARED_EXPERIENCE,
    "fact": MemoryType.USER_FACT,
}

PATTERNS: tuple[tuple[re.Pattern[str], MemoryType, int, str], ...] = (
    (
        re.compile(r"(?i)^my favou?rite\s+(.{2,60}?)\s+is\s+(.{1,180})[.!]?$"),
        MemoryType.USER_PREFERENCE,
        70,
        "favorite",
    ),
    (
        re.compile(r"(?i)^i (?:really )?(?:like|prefer)\s+(.{2,200})[.!]?$"),
        MemoryType.USER_PREFERENCE,
        55,
        "preference",
    ),
    (
        re.compile(r"(?i)^i (?:dislike|hate)\s+(.{2,200})[.!]?$"),
        MemoryType.USER_DISLIKE,
        65,
        "dislike",
    ),
    (
        re.compile(r"(?i)^i am allergic to\s+(.{2,160})[.!]?$"),
        MemoryType.USER_BOUNDARY,
        95,
        "allergy",
    ),
    (
        re.compile(r"(?i)^my goal is(?: to)?\s+(.{2,220})[.!]?$"),
        MemoryType.USER_GOAL,
        80,
        "goal",
    ),
    (
        re.compile(r"(?i)^i want to\s+(.{2,220})[.!]?$"),
        MemoryType.USER_GOAL,
        55,
        "goal",
    ),
    (
        re.compile(r"(?i)^i (usually|always|never)\s+(.{2,200})[.!]?$"),
        MemoryType.USER_HABIT,
        60,
        "habit",
    ),
    (
        re.compile(r"(?i)^my boundary is\s+(.{2,220})[.!]?$"),
        MemoryType.USER_BOUNDARY,
        90,
        "boundary",
    ),
    (
        re.compile(r"(?i)^i don'?t want\s+(.{2,220})[.!]?$"),
        MemoryType.USER_BOUNDARY,
        75,
        "boundary",
    ),
    (
        re.compile(
            r"(?i)^(?:please remember|don'?t forget)(?: that)?\s+(.{2,240})[.!]?$"
        ),
        MemoryType.USER_FACT,
        75,
        "remember",
    ),
    (
        re.compile(r"(?i)^i promised\s+(.{2,220})[.!]?$"),
        MemoryType.PROMISE,
        85,
        "promise",
    ),
    (
        re.compile(r"(?i)^we (?:decided|promised)\s+(.{2,220})[.!]?$"),
        MemoryType.COMMITMENT,
        85,
        "commitment",
    ),
)


def is_secret_like(content: str) -> bool:
    return bool(SECRET_RE.search(content))


def is_sensitive(content: str) -> bool:
    normalized = normalize_content(content)
    return bool(
        EMAIL_RE.search(content)
        or PHONE_RE.search(content)
        or any(
            term in normalized
            for term in ("allergic", "address", "medical", "diagnosed", "bank account")
        )
    )


def canonical_key(content: str, hint: str | None = None) -> str | None:
    normalized = normalize_content(content)
    favorite = re.match(r"my favou?rite\s+(.+?)\s+is\s+", normalized)
    if favorite:
        return f"favorite:{favorite.group(1)}"
    reverse_favorite = re.match(r".+?\s+is my favou?rite\s+(.+)", normalized)
    if reverse_favorite:
        return f"favorite:{reverse_favorite.group(1)}"
    if hint in {"allergy", "goal", "boundary", "preference", "dislike", "habit"}:
        return f"{hint}:{normalize_content(content)[:120]}"
    return None


def _acceptable(content: str, confidence: float, settings: Settings) -> bool:
    normalized = normalize_content(content)
    return bool(
        4 <= len(normalized) <= settings.memory_max_content_length
        and normalized not in GENERIC
        and not QUESTION_RE.search(content)
        and not HYPOTHETICAL_RE.search(content)
        and not QUOTED_RE.search(content)
        and not is_secret_like(content)
        and not PATH_RE.search(content)
        and confidence >= settings.memory_min_confidence_to_store
    )


class MemoryExtractionService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def deterministic(self, user_text: str) -> list[NormalizedCandidate]:
        if not self.settings.memory_deterministic_fact_extraction_enabled:
            return []
        text = display_content(user_text)
        if "\n" in user_text or HYPOTHETICAL_RE.search(text) or QUOTED_RE.search(text):
            return []
        for pattern, memory_type, importance, hint in PATTERNS:
            if pattern.fullmatch(text):
                sensitive = is_sensitive(text)
                if (
                    sensitive
                    and hint != "allergy"
                    and not self.settings.memory_enable_sensitive_auto_store
                ):
                    return []
                return [
                    NormalizedCandidate(
                        content=text,
                        normalized_content=normalize_content(text),
                        memory_type=memory_type,
                        importance=importance,
                        confidence=0.95,
                        tags=[hint],
                        source=MemorySource.DETERMINISTIC_USER_FACT,
                        canonical_fact_key=canonical_key(text, hint),
                        is_sensitive=sensitive,
                        reason="explicit_user_statement",
                    )
                ]
        return []

    def structured(
        self, candidates: Iterable[MemoryCandidate], user_text: str
    ) -> list[NormalizedCandidate]:
        results: list[NormalizedCandidate] = []
        evidence_tokens = set(normalize_content(user_text).split())
        for raw in list(candidates)[: self.settings.memory_max_candidates_per_exchange]:
            content = display_content(raw.content)
            candidate_tokens = set(normalize_content(content).split())
            overlap = len(candidate_tokens & evidence_tokens) / max(
                1, len(candidate_tokens)
            )
            confidence = min(
                float(raw.confidence or 0.7), 0.85 if overlap >= 0.35 else 0.4
            )
            kind = ALIASES.get(raw.memory_type.casefold())
            if kind is None:
                try:
                    kind = MemoryType(raw.memory_type.casefold())
                except ValueError:
                    continue
            importance = min(90, max(0, int(raw.importance)))
            sensitive = bool(raw.is_sensitive) or is_sensitive(content)
            if not _acceptable(content, confidence, self.settings):
                continue
            if sensitive and not self.settings.memory_enable_sensitive_auto_store:
                continue
            if importance < self.settings.memory_min_importance_to_store:
                continue
            results.append(
                NormalizedCandidate(
                    content=content,
                    normalized_content=normalize_content(content),
                    memory_type=kind,
                    importance=importance,
                    confidence=confidence,
                    tags=normalize_tags(
                        raw.tags,
                        limit=self.settings.memory_max_tags,
                        max_length=self.settings.memory_max_tag_length,
                    ),
                    entities=normalize_tags(raw.entities, limit=10, max_length=80),
                    source=MemorySource.MODEL_CANDIDATE,
                    canonical_fact_key=canonical_key(content),
                    is_sensitive=sensitive,
                    reason=raw.reason,
                )
            )
        return results

    def extract(
        self, user_text: str, model_candidates: Iterable[MemoryCandidate]
    ) -> list[NormalizedCandidate]:
        combined = self.deterministic(user_text) + self.structured(
            model_candidates, user_text
        )
        unique: dict[tuple[str, str], NormalizedCandidate] = {}
        for item in combined:
            unique.setdefault((item.memory_type.value, item.normalized_content), item)
        return list(unique.values())[: self.settings.memory_max_candidates_per_exchange]
