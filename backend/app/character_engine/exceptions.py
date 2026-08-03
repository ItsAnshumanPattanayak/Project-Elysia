class CharacterEngineError(Exception):
    """Base error for safe character-engine failures."""


class CharacterNotFoundError(CharacterEngineError):
    pass


class RoleplayProfileNotFoundError(CharacterEngineError):
    pass


class CharacterConfigurationError(CharacterEngineError):
    pass


class UnsupportedCharacterSchemaVersionError(CharacterConfigurationError):
    pass


class UnsafeCharacterPathError(CharacterEngineError):
    pass
