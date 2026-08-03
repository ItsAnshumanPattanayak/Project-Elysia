import hashlib
import re
import unicodedata

TOKEN_RE = re.compile(r"[\w']+", re.UNICODE)
SPACE_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"[^\w\s']", re.UNICODE)


def display_content(value: str) -> str:
    return SPACE_RE.sub(" ", unicodedata.normalize("NFKC", value)).strip()


def normalize_content(value: str) -> str:
    text = display_content(value).casefold()
    text = PUNCT_RE.sub(" ", text)
    return SPACE_RE.sub(" ", text).strip()


def tokens(value: str) -> set[str]:
    return {token.casefold() for token in TOKEN_RE.findall(value) if len(token) > 1}


def normalize_tags(
    values: list[str], *, limit: int = 10, max_length: int = 50
) -> list[str]:
    result: list[str] = []
    for value in values:
        tag = normalize_content(value)[:max_length]
        if tag and tag not in result:
            result.append(tag)
        if len(result) == limit:
            break
    return result


def application_hash(*parts: object) -> str:
    raw = "\x1f".join(str(part) for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
