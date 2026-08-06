"""
Rolling short-term message buffer. Separate from Scratchpad -- pruning
here (by whatever context_eval/ strategy is chosen later) must never
reach into scratchpad state.
"""

from dataclasses import dataclass, field


@dataclass
class Message:
    role: str   # "user" | "assistant" | "tool"
    content: str


class ShortTermBuffer:
    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages
        self._messages: list[Message] = []

    def add(self, role: str, content: str):
        self._messages.append(Message(role, content))
        self._prune_if_needed()

    def _prune_if_needed(self):
        # Simple sliding-window prune by default. context_eval/ will
        # swap this for whichever of the four strategies wins the
        # comparison table -- this is just the buffer's own default,
        # not the final strategy choice.
        overflow = len(self._messages) - self.max_messages
        if overflow > 0:
            self._messages = self._messages[overflow:]

    @property
    def messages(self) -> list[Message]:
        return list(self._messages)

    def as_transcript(self) -> str:
        return "\n".join(f"{m.role}: {m.content}" for m in self._messages)
