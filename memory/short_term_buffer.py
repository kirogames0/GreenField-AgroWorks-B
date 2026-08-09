"""
Rolling short-term message buffer. Separate from Scratchpad -- pruning
here (by whatever context_eval/ strategy is chosen later) must never
reach into scratchpad state.
"""

from dataclasses import dataclass

from context_eval.strategies.observation_masking import mask_old_tool_outputs
from memory.promote_or_drop import route_overflow_items


@dataclass
class Message:
    role: str   # "user" | "assistant" | "tool"
    content: str


class ShortTermBuffer:
    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages
        self._messages: list[Message] = []
        self.overflow_decisions: list[dict] = []
        self.episodic_promotions: list[dict] = []
        self._processed_overflow_count = 0

    def add(self, role: str, content: str):
        self._messages.append(Message(role, content))
        self._prune_if_needed()

    def _prune_if_needed(self):
        # Use the empirically validated observation-masking strategy as the
        # default pruning behavior. This preserves critical dialogue while
        # compacting older tool output, matching the context_eval comparison
        # results.
        overflow = len(self._messages) - self.max_messages
        if overflow > 0:
            overflow_items = self._messages[:overflow]
            decisions = route_overflow_items(overflow_items)
            self.overflow_decisions.extend(decisions)
            self.episodic_promotions.extend(
                decision for decision in decisions if decision["action"] == "promote_to_episodic"
            )
            self._messages = self._messages[overflow:]
            self._messages = mask_old_tool_outputs(self._messages, keep_last_n_tool_outputs=3)

    def take_new_overflow_decisions(self) -> list[dict]:
        new_decisions = self.overflow_decisions[self._processed_overflow_count:]
        self._processed_overflow_count = len(self.overflow_decisions)
        return new_decisions

    @property
    def messages(self) -> list[Message]:
        return list(self._messages)

    def as_transcript(self) -> str:
        return "\n".join(f"{m.role}: {m.content}" for m in self._messages)
