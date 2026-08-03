import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from app.services.conversation_errors import ConversationBusyError


@dataclass
class _LockEntry:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    users: int = 0


class ConversationLockService:
    def __init__(self) -> None:
        self._entries: dict[int, _LockEntry] = {}
        self._registry_lock = asyncio.Lock()

    @asynccontextmanager
    async def acquire(
        self, conversation_id: int, timeout_seconds: float
    ) -> AsyncIterator[None]:
        async with self._registry_lock:
            entry = self._entries.setdefault(conversation_id, _LockEntry())
            entry.users += 1
        acquired = False
        try:
            try:
                await asyncio.wait_for(entry.lock.acquire(), timeout_seconds)
                acquired = True
            except TimeoutError as exc:
                raise ConversationBusyError(
                    "Another generation is already running for this conversation."
                ) from exc
            yield
        finally:
            if acquired:
                entry.lock.release()
            async with self._registry_lock:
                entry.users -= 1
                if entry.users == 0 and not entry.lock.locked():
                    self._entries.pop(conversation_id, None)

    @property
    def registry_size(self) -> int:
        return len(self._entries)


conversation_lock_service = ConversationLockService()
