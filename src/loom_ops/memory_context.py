from __future__ import annotations

from loom_ops.config import Settings
from loom_ops.memory import MemoryStore
from loom_ops.state import Message


def memory_prefix_messages(settings: Settings) -> tuple[Message, ...]:
    if not settings.memory_enabled:
        return ()
    store = MemoryStore.for_workspace(settings.workspace)
    context = store.format_for_prompt()
    if not context:
        return ()
    return (Message(role="user", content=context),)
