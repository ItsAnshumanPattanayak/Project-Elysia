class MemoryError(Exception):
    code = "memory_application_failed"
    status_code = 400

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class MemoryNotFoundError(MemoryError):
    code = "memory_not_found"
    status_code = 404


class MemoryConversationMismatchError(MemoryError):
    code = "memory_conversation_mismatch"
    status_code = 404


class InvalidMemoryContentError(MemoryError):
    code = "invalid_memory_content"
    status_code = 422


class SecretLikeMemoryRejectedError(MemoryError):
    code = "secret_like_memory_rejected"
    status_code = 422


class MemoryDuplicateError(MemoryError):
    code = "memory_duplicate"
    status_code = 409


class MemoryLockedError(MemoryError):
    code = "memory_locked"
    status_code = 409


class MemoryRebuildConfirmationError(MemoryError):
    code = "memory_rebuild_confirmation_required"
    status_code = 409
