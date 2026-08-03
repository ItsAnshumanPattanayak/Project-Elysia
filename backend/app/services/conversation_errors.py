from typing import Any


class ConversationError(Exception):
    code = "conversation_error"
    status_code = 400
    retryable = False

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConversationNotFoundError(ConversationError):
    code = "conversation_not_found"
    status_code = 404


class ConversationArchivedError(ConversationError):
    code = "conversation_archived"
    status_code = 409


class ConversationInactiveError(ConversationError):
    code = "conversation_inactive"
    status_code = 409


class ConversationBusyError(ConversationError):
    code = "conversation_busy"
    status_code = 409
    retryable = True


class MessageNotFoundError(ConversationError):
    code = "message_not_found"
    status_code = 404


class MessageConversationMismatchError(ConversationError):
    code = "message_conversation_mismatch"
    status_code = 409


class InvalidMessageSenderError(ConversationError):
    code = "invalid_message_sender"
    status_code = 409


class MessageEditRequiresTruncationError(ConversationError):
    code = "message_edit_requires_truncation"
    status_code = 409


class MessageDeleteRequiresTruncationError(ConversationError):
    code = "message_delete_requires_truncation"
    status_code = 409


class DuplicateClientMessageError(ConversationError):
    code = "duplicate_client_message"
    status_code = 409


class RegenerateNotAllowedError(ConversationError):
    code = "regenerate_not_allowed"
    status_code = 409


class NoCharacterResponseToRegenerateError(ConversationError):
    code = "no_character_response_to_regenerate"
    status_code = 409


class ResponsePersistenceError(ConversationError):
    code = "response_persistence_failed"
    status_code = 500
    retryable = True


class StreamOutputLimitError(ConversationError):
    code = "generation_failed"
    status_code = 502


class InvalidPaginationError(ConversationError):
    code = "invalid_pagination"
    status_code = 422
